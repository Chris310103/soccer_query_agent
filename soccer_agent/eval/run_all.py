from soccer_agent.core.config import has_gemini_api_key
from soccer_agent.eval.run_benchmark import main as run_strict_benchmark
from soccer_agent.eval.product_benchmark import main as run_product_benchmark


def main():
    print("\n" + "=" * 100)
    print("RUNNING STRICT BENCHMARK")
    print("=" * 100)
    run_strict_benchmark()

    if has_gemini_api_key():
        print("\n" + "=" * 100)
        print("RUNNING PRODUCT BENCHMARK")
        print("=" * 100)
        run_product_benchmark()
    else:
        print("\n" + "=" * 100)
        print("SKIPPING PRODUCT BENCHMARK")
        print("=" * 100)
        print("No GEMINI_API_KEY / GOOGLE_API_KEY found.")
        print("Strict benchmark completed successfully.")
        print("Product benchmark is optional and requires a Gemini API key.")


if __name__ == "__main__":
    main()