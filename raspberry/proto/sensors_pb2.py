# Generated-compatible Protobuf module for proto/sensors.proto.
# Source of truth expected by the assignment:
# package iot; messages AccelSample, TempSample, SensorEnvelope.

from google.protobuf import descriptor_pb2 as _descriptor_pb2
from google.protobuf import descriptor_pool as _descriptor_pool
from google.protobuf import message as _message
from google.protobuf import reflection as _reflection
from google.protobuf import symbol_database as _symbol_database

_sym_db = _symbol_database.Default()


def _build_file_descriptor():
    file_proto = _descriptor_pb2.FileDescriptorProto()
    file_proto.name = "sensors.proto"
    file_proto.package = "iot"
    file_proto.syntax = "proto3"

    accel = file_proto.message_type.add()
    accel.name = "AccelSample"
    field = accel.field.add()
    field.name = "timestamp_ms"
    field.number = 1
    field.label = _descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = _descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    for name, number in (("ax", 2), ("ay", 3), ("az", 4)):
        field = accel.field.add()
        field.name = name
        field.number = number
        field.label = _descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
        field.type = _descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT

    temp = file_proto.message_type.add()
    temp.name = "TempSample"
    field = temp.field.add()
    field.name = "timestamp_ms"
    field.number = 1
    field.label = _descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = _descriptor_pb2.FieldDescriptorProto.TYPE_UINT32
    field = temp.field.add()
    field.name = "temperature"
    field.number = 2
    field.label = _descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = _descriptor_pb2.FieldDescriptorProto.TYPE_FLOAT

    env = file_proto.message_type.add()
    env.name = "SensorEnvelope"
    oneof = env.oneof_decl.add()
    oneof.name = "payload"
    field = env.field.add()
    field.name = "source_id"
    field.number = 1
    field.label = _descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = _descriptor_pb2.FieldDescriptorProto.TYPE_STRING
    field = env.field.add()
    field.name = "accel"
    field.number = 2
    field.label = _descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = _descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    field.type_name = ".iot.AccelSample"
    field.oneof_index = 0
    field = env.field.add()
    field.name = "temp"
    field.number = 3
    field.label = _descriptor_pb2.FieldDescriptorProto.LABEL_OPTIONAL
    field.type = _descriptor_pb2.FieldDescriptorProto.TYPE_MESSAGE
    field.type_name = ".iot.TempSample"
    field.oneof_index = 0

    return file_proto.SerializeToString()


DESCRIPTOR = _descriptor_pool.Default().AddSerializedFile(_build_file_descriptor())

AccelSample = _reflection.GeneratedProtocolMessageType(
    "AccelSample",
    (_message.Message,),
    {"DESCRIPTOR": DESCRIPTOR.message_types_by_name["AccelSample"], "__module__": "proto.sensors_pb2"},
)
TempSample = _reflection.GeneratedProtocolMessageType(
    "TempSample",
    (_message.Message,),
    {"DESCRIPTOR": DESCRIPTOR.message_types_by_name["TempSample"], "__module__": "proto.sensors_pb2"},
)
SensorEnvelope = _reflection.GeneratedProtocolMessageType(
    "SensorEnvelope",
    (_message.Message,),
    {"DESCRIPTOR": DESCRIPTOR.message_types_by_name["SensorEnvelope"], "__module__": "proto.sensors_pb2"},
)

_sym_db.RegisterMessage(AccelSample)
_sym_db.RegisterMessage(TempSample)
_sym_db.RegisterMessage(SensorEnvelope)
