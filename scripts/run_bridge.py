
import asyncio, argparse
from steelcity_impact_bridge.bridge import run

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", required=True)
    args = ap.parse_args()
    asyncio.run(run(args.config))

if __name__ == "__main__":
    main()
