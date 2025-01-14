# Generated by the gRPC Python protocol compiler plugin. DO NOT EDIT!
"""Client and server classes corresponding to protobuf-defined services."""
import grpc

from isolate.connections.grpc.definitions import common_pb2 as common__pb2
from isolate.server.definitions import server_pb2 as server__pb2


class IsolateStub(object):
    """Missing associated documentation comment in .proto file."""

    def __init__(self, channel):
        """Constructor.

        Args:
            channel: A grpc.Channel.
        """
        self.Run = channel.unary_stream(
                '/Isolate/Run',
                request_serializer=server__pb2.BoundFunction.SerializeToString,
                response_deserializer=common__pb2.PartialRunResult.FromString,
                )
        self.Submit = channel.unary_unary(
                '/Isolate/Submit',
                request_serializer=server__pb2.SubmitRequest.SerializeToString,
                response_deserializer=server__pb2.SubmitResponse.FromString,
                )
        self.SetMetadata = channel.unary_unary(
                '/Isolate/SetMetadata',
                request_serializer=server__pb2.SetMetadataRequest.SerializeToString,
                response_deserializer=server__pb2.SetMetadataResponse.FromString,
                )
        self.List = channel.unary_unary(
                '/Isolate/List',
                request_serializer=server__pb2.ListRequest.SerializeToString,
                response_deserializer=server__pb2.ListResponse.FromString,
                )
        self.Cancel = channel.unary_unary(
                '/Isolate/Cancel',
                request_serializer=server__pb2.CancelRequest.SerializeToString,
                response_deserializer=server__pb2.CancelResponse.FromString,
                )


class IsolateServicer(object):
    """Missing associated documentation comment in .proto file."""

    def Run(self, request, context):
        """Run the given function on the specified environment. Streams logs
        and the result originating from that function.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Submit(self, request, context):
        """Submit a function to be run without waiting for results.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def SetMetadata(self, request, context):
        """Set the metadata for a task.
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def List(self, request, context):
        """List running tasks
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')

    def Cancel(self, request, context):
        """Cancel a running task
        """
        context.set_code(grpc.StatusCode.UNIMPLEMENTED)
        context.set_details('Method not implemented!')
        raise NotImplementedError('Method not implemented!')


def add_IsolateServicer_to_server(servicer, server):
    rpc_method_handlers = {
            'Run': grpc.unary_stream_rpc_method_handler(
                    servicer.Run,
                    request_deserializer=server__pb2.BoundFunction.FromString,
                    response_serializer=common__pb2.PartialRunResult.SerializeToString,
            ),
            'Submit': grpc.unary_unary_rpc_method_handler(
                    servicer.Submit,
                    request_deserializer=server__pb2.SubmitRequest.FromString,
                    response_serializer=server__pb2.SubmitResponse.SerializeToString,
            ),
            'SetMetadata': grpc.unary_unary_rpc_method_handler(
                    servicer.SetMetadata,
                    request_deserializer=server__pb2.SetMetadataRequest.FromString,
                    response_serializer=server__pb2.SetMetadataResponse.SerializeToString,
            ),
            'List': grpc.unary_unary_rpc_method_handler(
                    servicer.List,
                    request_deserializer=server__pb2.ListRequest.FromString,
                    response_serializer=server__pb2.ListResponse.SerializeToString,
            ),
            'Cancel': grpc.unary_unary_rpc_method_handler(
                    servicer.Cancel,
                    request_deserializer=server__pb2.CancelRequest.FromString,
                    response_serializer=server__pb2.CancelResponse.SerializeToString,
            ),
    }
    generic_handler = grpc.method_handlers_generic_handler(
            'Isolate', rpc_method_handlers)
    server.add_generic_rpc_handlers((generic_handler,))


 # This class is part of an EXPERIMENTAL API.
class Isolate(object):
    """Missing associated documentation comment in .proto file."""

    @staticmethod
    def Run(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_stream(request, target, '/Isolate/Run',
            server__pb2.BoundFunction.SerializeToString,
            common__pb2.PartialRunResult.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Submit(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Isolate/Submit',
            server__pb2.SubmitRequest.SerializeToString,
            server__pb2.SubmitResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def SetMetadata(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Isolate/SetMetadata',
            server__pb2.SetMetadataRequest.SerializeToString,
            server__pb2.SetMetadataResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def List(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Isolate/List',
            server__pb2.ListRequest.SerializeToString,
            server__pb2.ListResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)

    @staticmethod
    def Cancel(request,
            target,
            options=(),
            channel_credentials=None,
            call_credentials=None,
            insecure=False,
            compression=None,
            wait_for_ready=None,
            timeout=None,
            metadata=None):
        return grpc.experimental.unary_unary(request, target, '/Isolate/Cancel',
            server__pb2.CancelRequest.SerializeToString,
            server__pb2.CancelResponse.FromString,
            options, channel_credentials,
            insecure, call_credentials, compression, wait_for_ready, timeout, metadata)
