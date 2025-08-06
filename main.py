import yaml
import sys
import os

# Add the 'src' directory to the Python path to allow for module imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'src'))

try:
    from femm_runner import run_femm_simulations
    from modelica_runner import run_modelica_simulations
    from post_processor import generate_plots
    from report_generator import generate_reports
except ImportError as e:
    print(f"Error: Failed to import a module from 'src'. Make sure 'src' directory is accessible.")
    print(f"Details: {e}")
    sys.exit(1)

def main():
    """
    Main function to orchestrate the entire simulation and analysis pipeline.
    """
    print("=====================================================")
    print("===   BLDC Motor Simulation and Analysis Pipeline   ===")
    print("=====================================================")

    # --- 1. Load Configuration ---
    config_path = 'config/params.yaml'
    print(f"\n[1/5] Loading configuration from '{config_path}'...")
    try:
        with open(config_path, 'r') as f:
            config = yaml.safe_load(f)
        print("  -> Configuration loaded successfully.")
    except FileNotFoundError:
        print(f"\n[Error] Configuration file not found at '{config_path}'.")
        print("Please ensure the file exists and you are running this script from the project root.")
        return

    # --- 2. Run FEMM Simulations ---
    print("\n[2/5] Starting FEMM simulation stage...")
    # A check to inform the user about the DXF file requirement
    cad_path = config.get('paths', {}).get('cad', 'cad')
    if not os.path.exists(cad_path) or not os.listdir(cad_path):
        print(f"  [CRITICAL] The '{cad_path}' directory is empty or does not exist.")
        print("  Please add the required motor DXF files to this directory before running.")
        # We can choose to exit here, or let the femm_runner handle the warning.
        # Letting femm_runner handle it is more graceful.
    run_femm_simulations(config)

    # --- 3. Run OpenModelica Simulations ---
    print("\n[3/5] Starting OpenModelica simulation stage...")
    run_modelica_simulations(config)

    # --- 4. Post-Process Results and Generate Plots ---
    print("\n[4/5] Starting post-processing and plot generation stage...")
    generate_plots(config)

    # --- 5. Generate Final PDF Reports ---
    print("\n[5/5] Starting final report generation stage...")
    generate_reports(config)

    print("\n=====================================================")
    print("===      Pipeline execution has finished.         ===")
    print("=====================================================")
    print(f"Final reports can be found in the '{config.get('paths',{}).get('report','report')}' directory.")


if __name__ == '__main__':
    main()
