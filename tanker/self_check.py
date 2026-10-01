import _paths  # noqa: F401

from benchkit.cli import self_check_main

if __name__ == "__main__":
    import metrics
    import sys

    argv = sys.argv[1:]
    if not any(arg == "--adapter" or arg.startswith("--adapter=") for arg in argv):
        argv = ["--adapter", "adapters.mine:MySolver", *argv]
    raise SystemExit(self_check_main(metrics.BENCH, argv))
