import base64
import struct
from proto import liqi_pb2 as pb

from enum import Enum
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message

class MsgType(Enum):
    """Game websocket message type"""

    Notify = 1
    Req = 2
    Res = 3

class LiqiParser:
    def __init__(self):
        self.mapResType = dict()
        pass

    def parse(self, content):
        # 解析消息头
        msg_type = MsgType(content[0])
        if msg_type == MsgType.Notify:
            msg_block = self.fromProtobuf(content[1:])
            method_name = msg_block[0]["data"].decode()
            prototype = self.protoTypeOf(method_name, msg_type)
            proto_obj = prototype.FromString(msg_block[1]["data"])
            dict_obj = MessageToDict(
                proto_obj,
                preserving_proto_field_name=True,
                including_default_value_fields=True,
            )
            if "data" in dict_obj:
                B = base64.b64decode(dict_obj["data"])
                action_proto_obj = getattr(pb, dict_obj["name"]).FromString(
                    self.decode(B)
                )
                action_dict_obj = MessageToDict(
                    action_proto_obj,
                    preserving_proto_field_name=True,
                    including_default_value_fields=True,
                )
                dict_obj["data"] = action_dict_obj
            msg_id = 0
        else:
            msg_id = struct.unpack("<H", content[1:3])[0]
            msg_block = self.fromProtobuf(content[3:])
            if msg_type == MsgType.Req:
                assert msg_id < 1 << 16
                assert len(msg_block) == 2
                assert(msg_id not in self.mapResType)
                method_name = msg_block[0]["data"].decode()
                prototype = self.protoTypeOf(method_name, msg_type)
                proto_obj = prototype.FromString(msg_block[1]["data"])
                dict_obj = MessageToDict(
                    proto_obj,
                    preserving_proto_field_name=True,
                    including_default_value_fields=True,
                )
                self.mapResType[msg_id] = (
                    method_name,
                    self.protoTypeOf(method_name, MsgType.Res),
                )
            elif msg_type == MsgType.Res:
                assert len(msg_block[0]["data"]) == 0
                assert msg_id in self.mapResType
                method_name, prototype = self.mapResType.pop(msg_id)
                proto_obj = prototype.FromString(msg_block[1]["data"])
                dict_obj = MessageToDict(
                    proto_obj,
                    preserving_proto_field_name=True,
                    including_default_value_fields=True,
                )
                if "game_restore" in dict_obj:
                    for action in dict_obj["game_restore"]["actions"]:
                        b64 = base64.b64decode(action["data"])
                        action_proto_obj = getattr(pb, action["name"]).FromString(b64)
                        action_dict_obj = MessageToDict(
                            action_proto_obj,
                            preserving_proto_field_name=True,
                            including_default_value_fields=True,
                        )
                        action["data"] = action_dict_obj
        return {"id":msg_id, "type":msg_type, "method":method_name, "data":dict_obj}

    @staticmethod
    def protoTypeOf(method_name: str, msg_type: MsgType) -> type[Message]:
        if msg_type == MsgType.Notify:
            _, lq, message_name = method_name.split(".")
            return getattr(pb, message_name)
        else:
            _, lq, service, rpc = method_name.split(".")
            method_desc = pb.DESCRIPTOR.services_by_name[service].methods_by_name[rpc]

            if msg_type == MsgType.Req:
                return getattr(pb, method_desc.input_type.name)
            elif msg_type == MsgType.Res:
                return getattr(pb, method_desc.output_type.name)


    @classmethod
    def fromProtobuf(cls, buf) -> list[dict]:
        p = 0
        result = []
        while p < len(buf):
            block_begin = p
            block_type = buf[p] & 7
            block_id = buf[p] >> 3
            p += 1
            if block_type == 0:
                block_type = "varint"
                data, p = cls.parseVarint(buf, p)
            elif block_type == 2:
                block_type = "string"
                s_len, p = cls.parseVarint(buf, p)
                data = buf[p : p + s_len]
                p += s_len
            else:
                raise Exception("unknow type:", block_type, "at", p)
            result.append(
                {"id": block_id, "type": block_type, "data": data, "begin": block_begin}
            )
        return result  
          
    @classmethod
    def toProtobuf(cls, data: list[dict]) -> bytes:
        result = b""
        for d in data:
            if d["type"] == "varint":
                result += ((d["id"] << 3) + 0).to_bytes(length=1, byteorder="little")
                result += cls.toVarint(d["data"])
            elif d["type"] == "string":
                result += ((d["id"] << 3) + 2).to_bytes(length=1, byteorder="little")
                result += cls.toVarint(len(d["data"]))
                result += d["data"]
            else:
                raise NotImplementedError
        return result

    @staticmethod
    def parseVarint(buf, p):
        data = 0
        base = 0
        while p < len(buf):
            data += (buf[p] & 127) << base
            base += 7
            p += 1
            if buf[p - 1] >> 7 == 0:
                break
        return (data, p)
    
    @staticmethod
    def toVarint(x: int) -> bytes:
        data = 0
        base = 0
        length = 0
        if x == 0:
            return b"\x00"
        while x > 0:
            length += 1
            data += (x & 127) << base
            x >>= 7
            if x > 0:
                data += 1 << (base + 7)
            base += 8
        return data.to_bytes(length, "little")

    @staticmethod
    def decode(data: bytes) -> bytes:
        keys = [0x84, 0x5E, 0x4E, 0x42, 0x39, 0xA2, 0x1F, 0x60, 0x1C]
        data = bytearray(data)
        for i in range(len(data)):
            u = (23 ^ len(data)) + 5 * i + keys[i % len(keys)] & 255
            data[i] ^= u
        return bytes(data)