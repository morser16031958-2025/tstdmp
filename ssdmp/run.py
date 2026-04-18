import sys

def main():
    from .cli import main as cli_main
    cli_main()

if __name__ == "__main__":
    main()
    sys.exit(0)