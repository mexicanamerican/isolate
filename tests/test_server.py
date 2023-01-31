import copy
import textwrap
from concurrent import futures
from contextlib import contextmanager
from functools import partial
from pathlib import Path
from typing import Any, List, Optional, cast

import grpc
import pytest

from isolate.backends.settings import IsolateSettings
from isolate.connections.grpc.configuration import get_default_options
from isolate.logs import Log, LogLevel, LogSource
from isolate.server import definitions
from isolate.server.interface import from_grpc, to_grpc, to_serialized_object
from isolate.server.server import BridgeManager, IsolateServicer

REPO_DIR = Path(__file__).parent.parent
assert (
    REPO_DIR.exists() and REPO_DIR.name == "isolate"
), "This test should have access to isolate as an installable package."


def inherit_from_local(monkeypatch: Any, value: bool = True) -> None:
    """Enables the inherit from local mode for the isolate server."""
    monkeypatch.setattr("isolate.server.server.INHERIT_FROM_LOCAL", value)


@contextmanager
def make_server(tmp_path):
    server = grpc.server(
        futures.ThreadPoolExecutor(max_workers=1), options=get_default_options()
    )
    test_settings = IsolateSettings(cache_dir=tmp_path / "cache")
    with BridgeManager() as bridge:
        definitions.register_isolate(IsolateServicer(bridge, test_settings), server)
        host, port = "localhost", server.add_insecure_port(f"[::]:0")
        server.start()

        try:
            yield definitions.IsolateStub(
                grpc.insecure_channel(
                    f"{host}:{port}",
                    options=get_default_options(),
                )
            )
        finally:
            server.stop(None)


@pytest.fixture
def stub(tmp_path):
    with make_server(tmp_path) as stub:
        yield stub


def define_environment(kind: str, **kwargs: Any) -> definitions.EnvironmentDefinition:
    struct = definitions.Struct()
    struct.update(kwargs)

    return definitions.EnvironmentDefinition(
        kind=kind,
        configuration=struct,
    )


_NOT_SET = object()


def run_request(
    stub: definitions.IsolateStub,
    request: definitions.BoundFunction,
    *,
    build_logs: Optional[List[Log]] = None,
    bridge_logs: Optional[List[Log]] = None,
    user_logs: Optional[List[Log]] = None,
) -> definitions.SerializedObject:
    log_store = {
        LogSource.BUILDER: build_logs if build_logs is not None else [],
        LogSource.BRIDGE: bridge_logs if bridge_logs is not None else [],
        LogSource.USER: user_logs if user_logs is not None else [],
    }

    return_value = _NOT_SET
    for result in stub.Run(request):
        for log in result.logs:
            log = from_grpc(log)
            log_store[log.source].append(log)

        if result.is_complete:
            if return_value is _NOT_SET:
                return_value = result.result
            else:
                raise ValueError("Sent the result twice")

    if return_value is _NOT_SET:
        raise ValueError("Never sent the result")
    else:
        return cast(definitions.SerializedObject, return_value)


def run_function(stub, function, *args, **kwargs):
    import __main__
    import dill

    dill.settings["recurse"] = True

    # Make it seem like it originated from __main__
    setattr(__main__, function.__name__, function)
    function.__module__ = "__main__"
    function.__qualname__ = f"__main__.{function.__name__}"

    basic_function = partial(function, *args, **kwargs)
    environment = define_environment("virtualenv", requirements=[])
    request = definitions.BoundFunction(
        function=to_serialized_object(basic_function, method="dill"),
        environments=[environment],
    )

    user_logs: List[Log] = []
    result = run_request(stub, request, user_logs=user_logs)

    raw_user_logs = [log.message for log in user_logs if log.message]
    return from_grpc(result), raw_user_logs


@pytest.mark.parametrize("inherit_local", [True, False])
def test_server_basic_communication(
    stub: definitions.IsolateStub,
    monkeypatch: Any,
    inherit_local: bool,
) -> None:
    inherit_from_local(monkeypatch, inherit_local)
    requirements = ["pyjokes==0.6.0"]
    if not inherit_local:
        # The agent process needs dill (and isolate) to actually
        # deserialize the given function, so they need to be installed
        # when we are not inheriting the local environment.
        requirements.append("dill==0.3.5.1")

        # TODO: apparently [server] doesn't work but [grpc] does work (not sure why
        # needs further investigation, probably poetry related).
        requirements.append(f"{REPO_DIR}[grpc]")

    env_definition = define_environment("virtualenv", requirements=requirements)
    request = definitions.BoundFunction(
        function=to_serialized_object(
            partial(
                eval,
                "__import__('pyjokes').__version__",
            ),
            method="dill",
        ),
        environments=[env_definition],
    )

    raw_result = run_request(stub, request)
    assert from_grpc(raw_result) == "0.6.0"


def test_server_builder_error(stub: definitions.IsolateStub, monkeypatch: Any) -> None:
    inherit_from_local(monkeypatch)

    # $$$$ as a package can't exist on PyPI since PEP 508 explicitly defines
    # what is considered to be a legit package name.
    #
    # https://peps.python.org/pep-0508/#names

    env_definition = define_environment("virtualenv", requirements=["$$$$"])
    request = definitions.BoundFunction(
        function=to_serialized_object(
            partial(
                eval,
                "__import__('pyjokes').__version__",
            ),
            method="dill",
        ),
        environments=[env_definition],
    )

    build_logs: List[Log] = []
    with pytest.raises(grpc.RpcError) as exc:
        run_request(stub, request, build_logs=build_logs)

    assert exc.match("A problem occurred while creating the environment")

    raw_logs = [log.message for log in build_logs]
    assert "ERROR: Invalid requirement: '$$$$'" in raw_logs


def test_user_logs_immediate(stub: definitions.IsolateStub, monkeypatch: Any) -> None:
    inherit_from_local(monkeypatch)

    env_definition = define_environment("virtualenv", requirements=["pyjokes==0.6.0"])
    request = definitions.BoundFunction(
        function=to_serialized_object(
            partial(
                exec,
                textwrap.dedent(
                    """
                import sys, pyjokes
                print(pyjokes.__version__)
                print("error error!", file=sys.stderr)
                """
                ),
            ),
            method="dill",
        ),
        environments=[env_definition],
    )

    user_logs: List[Log] = []
    run_request(stub, request, user_logs=user_logs)

    assert len(user_logs) == 2

    by_stream = {log.level: log.message for log in user_logs}
    assert by_stream[LogLevel.STDOUT] == "0.6.0"
    assert by_stream[LogLevel.STDERR] == "error error!"


def test_unknown_environment(stub: definitions.IsolateStub, monkeypatch: Any) -> None:
    inherit_from_local(monkeypatch)

    env_definition = define_environment("unknown")
    request = definitions.BoundFunction(
        function=to_serialized_object(
            partial(
                eval,
                "__import__('pyjokes').__version__",
            ),
            method="dill",
        ),
        environments=[env_definition],
    )

    with pytest.raises(grpc.RpcError) as exc:
        run_request(stub, request)

    assert exc.match("Unknown environment kind")


def test_invalid_param(stub: definitions.IsolateStub, monkeypatch: Any) -> None:
    inherit_from_local(monkeypatch)

    env_definition = define_environment("virtualenv", packages=["pyjokes==1.0"])
    request = definitions.BoundFunction(
        function=to_serialized_object(
            partial(
                eval,
                "__import__('pyjokes').__version__",
            ),
            method="dill",
        ),
        environments=[env_definition],
    )

    with pytest.raises(grpc.RpcError) as exc:
        run_request(stub, request)

    assert exc.match("unexpected keyword argument 'packages'")


@pytest.mark.parametrize("inherit_local", [True, False])
def test_server_multiple_envs(
    stub: definitions.IsolateStub,
    monkeypatch: Any,
    inherit_local: bool,
) -> None:
    inherit_from_local(monkeypatch, inherit_local)
    xtra_requirements = ["python-dateutil==2.8.2"]
    requirements = ["pyjokes==0.6.0"]
    if not inherit_local:
        # The agent process needs dill (and isolate) to actually
        # deserialize the given function, so they need to be installed
        # when we are not inheriting the local environment.
        requirements.append("dill==0.3.5.1")

        # TODO: apparently [server] doesn't work but [grpc] does work (not sure why
        # needs further investigation, probably poetry related).
        requirements.append(f"{REPO_DIR}[grpc]")

    env_definition = define_environment("virtualenv", requirements=requirements)
    xtra_env_definition = define_environment(
        "virtualenv", requirements=xtra_requirements
    )
    request = definitions.BoundFunction(
        function=to_serialized_object(
            partial(
                eval,
                "__import__('pyjokes').__version__ + ' ' + __import__('dateutil').__version__",
            ),
            method="dill",
        ),
        environments=[env_definition, xtra_env_definition],
    )

    raw_result = run_request(stub, request)

    assert from_grpc(raw_result) == "0.6.0 2.8.2"


@pytest.mark.parametrize("python_version", ["3.8"])
def test_agent_requirements_custom_version(
    stub: definitions.IsolateStub,
    monkeypatch: Any,
    python_version: str,
) -> None:
    requirements = ["pyjokes==0.6.0"]
    agent_requirements = ["dill==0.3.5.1", f"{REPO_DIR}[grpc]"]
    monkeypatch.setattr("isolate.server.server.AGENT_REQUIREMENTS", agent_requirements)

    env_definition = define_environment(
        "virtualenv",
        requirements=requirements,
        python_version=python_version,
    )
    request = definitions.BoundFunction(
        function=to_serialized_object(
            partial(
                eval,
                "__import__('sysconfig').get_python_version(), __import__('pyjokes').__version__",
            ),
            method="dill",
        ),
        environments=[env_definition],
    )

    raw_result = run_request(stub, request)
    assert from_grpc(raw_result) == ("3.8", "0.6.0")


def test_agent_show_logs_from_agent_requirements(
    stub: definitions.IsolateStub,
    monkeypatch: Any,
) -> None:
    requirements = ["pyjokes==0.6.0"]
    agent_requirements = ["$$$$", f"{REPO_DIR}[grpc]"]
    monkeypatch.setattr("isolate.server.server.AGENT_REQUIREMENTS", agent_requirements)

    env_definition = define_environment(
        "virtualenv",
        requirements=requirements,
    )
    request = definitions.BoundFunction(
        function=to_serialized_object(
            partial(
                eval,
                "__import__('sysconfig').get_python_version(), __import__('pyjokes').__version__",
            ),
            method="dill",
        ),
        environments=[env_definition],
    )

    build_logs: List[Log] = []
    with pytest.raises(grpc.RpcError) as exc:
        run_request(stub, request, build_logs=build_logs)

    assert exc.match("A problem occurred while creating the environment")

    raw_logs = [log.message for log in build_logs]
    assert "ERROR: Invalid requirement: '$$$$'" in raw_logs


def test_bridge_connection_reuse(
    stub: definitions.IsolateStub, monkeypatch: Any
) -> None:
    inherit_from_local(monkeypatch)

    first_env = define_environment(
        "virtualenv",
        requirements=["pyjokes==0.6.0"],
    )
    request = definitions.BoundFunction(
        setup_func=to_serialized_object(
            lambda: __import__("os").getpid(), method="cloudpickle"
        ),
        function=to_serialized_object(
            lambda process_pid: process_pid, method="cloudpickle"
        ),
        environments=[first_env],
    )

    initial_process_pid = from_grpc(run_request(stub, request))
    secondary_process_pid = from_grpc(run_request(stub, request))

    # Both of the functions should run in the same agent process
    assert initial_process_pid == secondary_process_pid

    # But if we run a third function that has a different environment
    # then its process should be different
    second_env = define_environment(
        "virtualenv",
        requirements=["pyjokes==0.5.0"],
    )
    request_2 = copy.deepcopy(request)
    request_2.environments.remove(first_env)
    request_2.environments.append(second_env)

    third_process_pid = from_grpc(run_request(stub, request_2))
    assert third_process_pid != initial_process_pid

    # As long as the environments are same, they are cached
    fourth_process_pid = from_grpc(run_request(stub, request_2))
    assert fourth_process_pid == third_process_pid


@pytest.mark.flaky(reruns=3)
def test_bridge_connection_reuse_logs(
    stub: definitions.IsolateStub, monkeypatch: Any
) -> None:
    inherit_from_local(monkeypatch)

    first_env = define_environment(
        "virtualenv",
        requirements=["pyjokes==0.6.0"],
    )
    request = definitions.BoundFunction(
        setup_func=to_serialized_object(
            lambda: print("setup"),
            method="cloudpickle",
        ),
        function=to_serialized_object(
            lambda _: print("run"),
            method="cloudpickle",
        ),
        environments=[first_env],
    )

    logs: List[Log] = []
    run_request(stub, request, user_logs=logs)
    run_request(stub, request, user_logs=logs)
    run_request(stub, request, user_logs=logs)

    str_logs = [log.message for log in logs if log.message]
    assert str_logs == [
        "setup",
        "run",
        "run",
        "run",
    ]


def print_logs_no_delay(num_lines, should_flush):
    for i in range(num_lines):
        print(i, flush=should_flush)

    return num_lines


@pytest.mark.parametrize("num_lines", [0, 1, 10, 100, 1000])
@pytest.mark.parametrize("should_flush", [True, False])
@pytest.mark.flaky(reruns=3)
def test_receive_complete_logs(
    stub: definitions.IsolateStub,
    monkeypatch: Any,
    num_lines: int,
    should_flush: bool,
) -> None:
    inherit_from_local(monkeypatch)
    result, logs = run_function(stub, print_logs_no_delay, num_lines, should_flush)
    assert result == num_lines
    assert logs == [str(i) for i in range(num_lines)]


def take_buffer(buffer):
    return buffer


def test_grpc_option_configuration(tmp_path, monkeypatch):
    inherit_from_local(monkeypatch)
    with monkeypatch.context() as ctx:
        ctx.setenv("ISOLATE_GRPC_CALL_MAX_SEND_MESSAGE_LENGTH", "100")
        ctx.setenv("ISOLATE_GRPC_CALL_MAX_RECEIVE_MESSAGE_LENGTH", "100")

        with pytest.raises(grpc.RpcError, match="Sent message larger than max"):
            with make_server(tmp_path) as stub:
                run_function(stub, take_buffer, b"0" * 200)

    with monkeypatch.context() as ctx:
        ctx.setenv("ISOLATE_GRPC_CALL_MAX_SEND_MESSAGE_LENGTH", "5000")
        ctx.setenv("ISOLATE_GRPC_CALL_MAX_RECEIVE_MESSAGE_LENGTH", "5000")

        with make_server(tmp_path) as stub:
            result, _ = run_function(stub, take_buffer, b"0" * 200)
            assert result == b"0" * 200
