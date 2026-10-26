"""Command line entry point: ``python -m slr.cli data|run``."""

import sys

from slr import manifest, pipeline


def main(argv=None):
    """``data`` only fills the cache; ``run`` does the full analysis."""
    command = (argv or sys.argv[1:] or ["run"])[0]
    if command == "data":
        cfg = pipeline.read_config("scenarios.yaml")
        paths = pipeline.fetch_sources(cfg)
        city, _, _ = pipeline.load_study_area(cfg, paths)
        pipeline.osm.fetch_sites(city, cfg["osm_tags"])
    elif command == "run":
        context = pipeline.run()
        outputs = sorted(context["out_dir"].glob("*.csv"))
        manifest.write_manifest(context, outputs)
        print(context["table"].to_string(index=False))
    else:
        raise SystemExit(f"Unknown command {command!r}; use 'data' or 'run'")


if __name__ == "__main__":
    main()
