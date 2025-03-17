import sys
import argparse
import subprocess

def main():
    parser = argparse.ArgumentParser(description="Generate and execute command to run parse.py with specified TEST-ID.")
    parser.add_argument('test_id', type=str, help="The TEST-ID to use for generating the command.")
    args = parser.parse_args()

    test_id = args.test_id
    input_file = f"{test_id}.input"
    output_file = f"{test_id}.output.xml"

    command = f"python3.11 parse.py <0input/{input_file} >0output/{output_file}"
    print(f"Executing: {command}")

    # Execute the command
    try:
        subprocess.run(command, shell=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"Error executing command: {e}", file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
