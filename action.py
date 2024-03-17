import time
import random
from convert import MS_TILE_2_MJAI_TILE
from functools import cmp_to_key
from majsoul2mjai import compare_pai
from loguru import logger

click_list = []
do_autohu = False

# Coordinates here is on the resolution of 16x9
LOCATION = {
    "tiles": [
        (2.23125  , 8.3625),
        (3.021875 , 8.3625),
        (3.8125   , 8.3625),
        (4.603125 , 8.3625),
        (5.39375  , 8.3625),
        (6.184375 , 8.3625),
        (6.975    , 8.3625),
        (7.765625 , 8.3625),
        (8.55625  , 8.3625),
        (9.346875 , 8.3625),
        (10.1375  , 8.3625),
        (10.928125, 8.3625),
        (11.71875 , 8.3625),
        (12.509375, 8.3625),
    ],
    "tsumo_space": 0.246875,
    "actions": [
        (10.875, 7), #none       #
        (8.6375, 7),             #   5   4   3
        (6.4   , 7),             #
        (10.875, 5.9),           #   2   1   0
        (8.6375, 5.9),           #
        (6.4   , 5.9),
        (10.875, 4.8),           # Not used
        (8.6375, 4.8),           # Not used
        (6.4   , 4.8),           # Not used
    ],
    "candidates": [
        (3.6625,  6.3),         # (-(len/2)+idx+0.5)*2+5
        (4.49625, 6.3),
        (5.33 ,   6.3),
        (6.16375, 6.3),
        (6.9975,  6.3),
        (7.83125, 6.3),         # 5 mid
        (8.665,   6.3),
        (9.49875, 6.3),
        (10.3325, 6.3),
        (11.16625,6.3),
        (12,      6.3),
    ],
    "candidates_kan": [
        (4.325,   6.3),         #
        (5.4915,  6.3),
        (6.6583,  6.3),
        (7.825,   6.3),         # 3 mid
        (8.9917,  6.3),
        (10.1583, 6.3),
        (11.325,  6.3),
    ],
}

# Refer to majsoul2mjai.Operation
ACTION_PIORITY = [
    0,  # none      #
    99, # Discard   # There is no discard button
    4,  # Chi       # Opponent Discard
    3,  # Pon       # Opponent Discard
    3,  # Ankan     # Self Discard      # If Ankan and Kakan are both available, use only kakan.
    2,  # Daiminkan # Opponent Discard
    3,  # Kakan     # Self Discard
    2,  # Reach     # Self Discard
    1,  # Zimo      # Self Discard
    1,  # Rong      # Opponent Discard
    5,  # Ryukyoku  # Self Discard
    4,  # Nukidora  # Self Discard
]

ACTION2TYPE = {
    "none": 0,
    "chi": 2,
    "pon": 3,
    "daiminkan": 5,
    "hora": 9,
    #^^^^^^^^^^^^^^^^Opponent Discard^^^^^^^^^^^^^^^^
    "ryukyoku": 10,
    "nukidora": 11,
    "ankan": 4,
    "kakan": 6,
    "reach": 7,
    "zimo": 8,
    #^^^^^^^^^^^^^^^^Self Discard^^^^^^^^^^^^^^^^
}

def get_click_list():
    return click_list

def get_autohu():
    return do_autohu

# with open("settings.json", "r") as f:
#     settings = json.load(f)
#     PLAYWRIGHT_RESOLUTION = (settings['Playwright']['width'], settings['Playwright']['height'])
#     SCALE = PLAYWRIGHT_RESOLUTION[0]/16

class Action:
    def __init__(self):
        self.isNewRound = True
        self.reached = False
        self.latest_operation_list = []
        pass

    def page_clicker(self, coord: tuple[float, float]):
        global click_list
        click_list.append(coord)

    def do_autohu(self):
        global do_autohu
        do_autohu = True

    def decide_random_time(self):
        if self.isNewRound:
            return random.uniform(3.0, 3.8)
        return random.uniform(1.9, 2.8)


    def click_chiponkan(self, mjai_msg: dict | None, tehai: list[str], tsumohai: str | None):
        latest_operation_list_temp = self.latest_operation_list.copy()
        latest_operation_list_temp.append({'type': 0, 'combination': []})
        can_ankan = False
        can_kakan = False
        ankan_combination = None
        # if both Ankan (type 4) and Kakan (type 6) are available
        for operation in self.latest_operation_list:
            if operation['type'] == 4:
                can_ankan = True
                ankan_combination = operation['combination']
            if operation['type'] == 6:
                can_kakan = True
        if can_ankan and can_kakan:
            for idx, operation in enumerate(self.latest_operation_list):
                if operation['type'] == 6:
                    latest_operation_list_temp[idx]['combination'] += ankan_combination
                if operation['type'] == 4:
                    latest_operation_list_temp.remove(operation)

        # Sort latest_operation_list by ACTION_PIORITY
        # logger.debug(f"latest_operation_list_temp: {latest_operation_list_temp}")
        latest_operation_list_temp.sort(key=lambda x: ACTION_PIORITY[x['type']])

        if tsumohai != '?' and mjai_msg['type'] == 'hora':
            mjai_msg['type'] = 'zimo'

        for idx, operation in enumerate(latest_operation_list_temp):
            if operation['type'] == ACTION2TYPE[mjai_msg['type']]:
                self.page_clicker(LOCATION['actions'][idx])
                self.do_autohu()
                self.isNewRound = False
                break

        if mjai_msg['type'] == 'reach':
            self.reached = True
            time.sleep(0.5)
            self.click_dahai(mjai_msg, tehai, tsumohai)
            return
        
        if mjai_msg['type'] in ['chi', 'pon', 'ankan', 'kakan']:
            consumed_pais_mjai = mjai_msg['consumed']
            consumed_pais_mjai = sorted(consumed_pais_mjai, key=cmp_to_key(compare_pai))
            if mjai_msg['type'] == 'chi':
                for operation in self.latest_operation_list:
                    if operation['type'] == 2:
                        combination_len = len(operation['combination'])
                        if combination_len == 1:
                            return  # No need to click
                        for idx, combination in enumerate(operation['combination']):
                            consumed_pais_liqi = [MS_TILE_2_MJAI_TILE[pai] for pai in combination.split('|')]
                            consumed_pais_liqi = sorted(consumed_pais_liqi, key=cmp_to_key(compare_pai))
                            if consumed_pais_mjai == consumed_pais_liqi:
                                time.sleep(0.3)
                                candidate_idx = int((-(combination_len/2)+idx+0.5)*2+5)
                                self.page_clicker(LOCATION['candidates'][candidate_idx])
                                return
            elif mjai_msg['type'] == 'pon':
                for operation in self.latest_operation_list:
                    if operation['type'] == 3:
                        combination_len = len(operation['combination'])
                        if combination_len == 1:
                            return
                        for idx, combination in enumerate(operation['combination']):
                            consumed_pais_liqi = [MS_TILE_2_MJAI_TILE[pai] for pai in combination.split('|')]
                            consumed_pais_liqi = sorted(consumed_pais_liqi, key=cmp_to_key(compare_pai))
                            if consumed_pais_mjai == consumed_pais_liqi:
                                time.sleep(0.3)
                                candidate_idx = int((-(combination_len/2)+idx+0.5)*2+5)
                                self.page_clicker(LOCATION['candidates'][candidate_idx])
                                return
            # If both Ankan (type 4) and Kakan (type 6) are available, only one kan button will be shown, and candidates = [kakan, ankan]
            elif mjai_msg['type'] in ['ankan', 'kakan']:
                if can_ankan and can_kakan:
                    for operation in latest_operation_list_temp:
                        if operation['type'] == 6:
                            combination_len = len(operation['combination'])
                            if combination_len == 1:
                                # impossible
                                return
                            for idx, combination in enumerate(operation['combination']):
                                consumed_pais_liqi = [MS_TILE_2_MJAI_TILE[pai] for pai in combination.split('|')]
                                consumed_pais_liqi = sorted(consumed_pais_liqi, key=cmp_to_key(compare_pai))
                                if consumed_pais_mjai == consumed_pais_liqi:
                                    time.sleep(0.3)
                                    candidate_idx = int((-(combination_len/2)+idx+0.5)*2+3)
                                    self.page_clicker(LOCATION['candidates_kan'][candidate_idx])
                                    return
                elif mjai_msg['type'] == 'ankan':
                    for operation in self.latest_operation_list:
                        if operation['type'] == 4:
                            combination_len = len(operation['combination'])
                            if combination_len == 1:
                                return
                            for idx, combination in enumerate(operation['combination']):
                                consumed_pais_liqi = [MS_TILE_2_MJAI_TILE[pai] for pai in combination.split('|')]
                                consumed_pais_liqi = sorted(consumed_pais_liqi, key=cmp_to_key(compare_pai))
                                if consumed_pais_mjai == consumed_pais_liqi:
                                    time.sleep(0.3)
                                    candidate_idx = int((-(combination_len/2)+idx+0.5)*2+3)
                                    self.page_clicker(LOCATION['candidates_kan'][candidate_idx])
                                    return
                elif mjai_msg['type'] == 'kakan':
                    for operation in self.latest_operation_list:
                        if operation['type'] == 6:
                            combination_len = len(operation['combination'])
                            if combination_len == 1:
                                return
                            for idx, combination in enumerate(operation['combination']):
                                consumed_pais_liqi = [MS_TILE_2_MJAI_TILE[pai] for pai in combination.split('|')]
                                consumed_pais_liqi = sorted(consumed_pais_liqi, key=cmp_to_key(compare_pai))
                                if consumed_pais_mjai == consumed_pais_liqi:
                                    time.sleep(0.3)
                                    candidate_idx = int((-(combination_len/2)+idx+0.5)*2+3)
                                    self.page_clicker(LOCATION['candidates_kan'][candidate_idx])
                                    return


    def get_pai_coord(self, idx: int, tehais: list[str]):
        tehai_count = 0
        for tehai in tehais:
            if tehai != '?':
                tehai_count += 1
        if tehai_count >= 14:
            tehai_count = 13
        if idx == 13:
            pai_cord = (LOCATION['tiles'][tehai_count][0] + LOCATION['tsumo_space'], LOCATION['tiles'][tehai_count][1])
        else:
            pai_cord = LOCATION['tiles'][idx]
        
        return pai_cord

    # tehai: 手牌 tsumohai：表示摸切的牌，即从牌山摸到的牌，并立刻打出。
    def click_dahai(self, mjai_msg: dict | None, tehai: list[str], tsumohai: str | None):
        dahai = mjai_msg['pai']
        if self.isNewRound:
            # In Majsoul, if you are the first dealer, there is no tsumohai, but 14 tehai.
            # However, in MJAI, there is 13 tehai and 1 tsumohai.
            temp_tehai = tehai.copy()
            temp_tehai.append(tsumohai)
            temp_tehai = sorted(temp_tehai, key=cmp_to_key(compare_pai))
            for i in range(14):
                if dahai == temp_tehai[i]:
                    logger.debug(f"dahai:{dahai} tehai:{tehai} tsumohai:{tsumohai} isNewRound:{self.isNewRound} i:{i}")
                    pai_coord = self.get_pai_coord(i, temp_tehai)
                    self.page_clicker(pai_coord)
                    self.do_autohu()
                    self.isNewRound = False
                    return
        if tsumohai != '?':
            if dahai == tsumohai:
                logger.debug(f"dahai:{dahai} tehai:{tehai} tsumohai:{tsumohai} isNewRound:{self.isNewRound} dahai== tsumohai")
                pai_coord = self.get_pai_coord(13, tehai)
                self.page_clicker(pai_coord)
                return
        for i in range(13):
            if dahai == tehai[i]:
                logger.debug(f"dahai:{dahai} tehai:{tehai} tsumohai:{tsumohai} isNewRound:{self.isNewRound} i:{i}")
                pai_coord = self.get_pai_coord(i, tehai)
                self.page_clicker(pai_coord)
                break
        

    def mjai2action(self, mjai_msg: dict | None, tehai: list[str], tsumohai: str | None):
        # print(f"mjai2action: mjai_msg:{mjai_msg} tehai:{tehai} tsomohai:{tsumohai}")
        # 将字符串解析为字典
        dahai_delay = self.decide_random_time()     
        if mjai_msg is None:
            return
        mtype = mjai_msg['type']
        if mtype == 'dahai' and not self.reached:
            time.sleep(dahai_delay)
            self.click_dahai(mjai_msg, tehai, tsumohai)
            return
        # 这里是mjai的events
        # https://mjai.app/docs/mjai-protocol#:~:text=Flowchart-,Events,-Start%20Game
        if mtype in ['none', 'chi', 'pon', 'daiminkan', 'ankan', 'kakan', 'hora', 'reach', 'ryukyoku', 'nukidora']:
            time.sleep(random.uniform(2.3, 2.5))
            self.click_chiponkan(mjai_msg, tehai, tsumohai)
            # kan can have multiple candidates too! ex: tehai=1111m 1111p 111s 11z, tsumohai=1s
        