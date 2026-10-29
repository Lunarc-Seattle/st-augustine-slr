"""Command line entry point: ``slr data|run`` (or ``python -m slr.cli``)."""

import argparse

from slr import figures, manifest, pipeline


def main(argv=None):
    """``data`` only fills the cache; ``run`` does the full analysis."""
    parser = argparse.ArgumentParser(prog="slr", description=__doc__)
    parser.add_argument("command", nargs="?", default="run", choices=["data", "run"])
    parser.add_argument("--config", default="scenarios.yaml", help="scenario file (default: %(default)s)")
    parser.add_argument("--out", default="outputs", help="output directory (default: %(default)s)")
    args = parser.parse_args(argv)

    if args.command == "data":
        cfg = pipeline.read_config(args.config)
        paths = pipeline.fetch_sources(cfg)
        city, _, _ = pipeline.load_study_area(cfg, paths)
        pipeline.osm.fetch_sites(city, cfg["osm_tags"], endpoint=cfg.get("overpass_url"))
    else:
        context = pipeline.run(args.config, args.out)
        outputs = sorted(context["out_dir"].glob("*.csv")) + figures.make_all(context)
        manifest.write_manifest(context, outputs)
        print(context["table"].to_string(index=False))


if __name__ == "__main__":
    main()
