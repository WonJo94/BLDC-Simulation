import os
import shutil
import subprocess
from typing import Dict, Any
import math

# Note: The original prompt used OMPython. However, OMPython can sometimes be
# complex to set up and use for batch processing. A more robust and common
# approach for batch simulations in OpenModelica is to use its scripting
# interface (`omc`) via a command-line call. This avoids potential ZMQ issues
# and is generally more stable for automation. We will use this subprocess approach.

def _create_simulation_script(model_name: str, stop_time: float, output_path: str) -> str:
    """Creates an OpenModelica scripting file (.mos) to run a simulation."""
    script_content = f"""
loadModel(Modelica);
getErrorString();
loadFile("{model_name}.mo");
getErrorString();
simulate({model_name}, startTime=0, stopTime={stop_time}, outputFormat="csv", fileNamePrefix="{output_path}");
getErrorString();
"""
    return script_content

def run_modelica_simulations(config: Dict[str, Any]):
    """
    Runs a batch of OpenModelica simulations based on the config.
    """
    print("\n--- Starting OpenModelica Simulation Batch ---")

    paths = config['paths']
    sim_params = config['simulation_params']['system']

    # Ensure the results directory exists
    results_dir = paths['results']
    os.makedirs(results_dir, exist_ok=True)

    # Read the Modelica model template
    try:
        with open(paths['modelica_model_template'], 'r') as f:
            model_template = f.read()
    except FileNotFoundError:
        print(f"[Error] Modelica template not found at '{paths['modelica_model_template']}'. Aborting.")
        return

    # Path to the OpenModelica Compiler
    # This assumes 'omc' is in the system's PATH. If not, the full path should be provided.
    omc_path = "omc"

    for motor_id, motor_params in config['motors'].items():
        print(f"\nProcessing motor: {motor_id}")

        # Find the nominal FEMM results file (no geometric errors)
        nominal_case_name = f"{motor_id}_static_0p0_dyn_0p0_tilt_0p0.csv"
        torque_map_path = os.path.join(results_dir, nominal_case_name)

        if not os.path.exists(torque_map_path):
            print(f"  [Warning] Nominal torque map '{torque_map_path}' not found. Skipping system simulations for this motor.")
            continue

        # Windows paths need to be escaped for Modelica
        torque_map_path_modelica = torque_map_path.replace('\\', '/')

        # Iterate through all system simulation cases
        for controller in sim_params['controllers']:
            for freq_khz in sim_params['hil_freq_kHz']:
                for rpm in sim_params['speed_rpm']:

                    case_name = f"{motor_id}_{controller}_{freq_khz}kHz_{rpm}rpm"
                    print(f"  Running case: {case_name}")

                    # --- Prepare Modelica File ---
                    hil_ts = 1.0 / (freq_khz * 1000.0)
                    target_rad_s = rpm * 2 * math.pi / 60
                    encoder_res = 2**sim_params['encoder_bits']

                    model_content = model_template.format(
                        csv_file_path=torque_map_path_modelica,
                        motor_poles=motor_params['poles'],
                        target_speed_rad_per_s=target_rad_s,
                        hil_ts=hil_ts,
                        encoder_resolution=encoder_res,
                        controller_type=controller
                    )

                    # Define a temporary model name and path
                    temp_model_name = f"Temp_{case_name}"
                    temp_model_path = os.path.join(results_dir, f"{temp_model_name}.mo")
                    with open(temp_model_path, 'w') as f:
                        f.write(model_content)

                    # --- Prepare and Run Simulation Script ---
                    sim_output_prefix = os.path.join(results_dir, case_name)
                    mos_script_content = _create_simulation_script(
                        model_name=f"EccentricityStudy.{temp_model_name}",
                        stop_time=sim_params['sim_time_s'],
                        output_path=sim_output_prefix
                    )

                    temp_script_path = os.path.join(results_dir, "run_sim.mos")
                    with open(temp_script_path, 'w') as f:
                        f.write(mos_script_content)

                    # Run the simulation using omc
                    try:
                        # The command needs to be run in a directory that allows access
                        # to the package. We assume the top level has a package.mo
                        # that defines EccentricityStudy.
                        # For simplicity, we run it from the root.
                        # We also need to tell omc where to find the EccentricityStudy package.
                        # A simple way is to create a package.mo in the root.
                        if not os.path.exists("package.mo"):
                            with open("package.mo", "w") as f:
                                f.write("within; package EccentricityStudy end EccentricityStudy;")

                        cmd = [omc_path, temp_script_path]
                        subprocess.run(cmd, check=True, capture_output=True, text=True)
                        print(f"    -> Simulation successful. Output: {sim_output_prefix}_res.csv")
                    except FileNotFoundError:
                        print(f"[Error] '{omc_path}' not found. Is OpenModelica installed and in your PATH?")
                        return # Abort if omc is not found
                    except subprocess.CalledProcessError as e:
                        print(f"    [Error] OpenModelica simulation failed for case: {case_name}")
                        print(f"    OMC Stderr: {e.stderr}")
                    finally:
                        # Clean up temporary files
                        if os.path.exists(temp_model_path):
                            os.remove(temp_model_path)
                        if os.path.exists(temp_script_path):
                            os.remove(temp_script_path)

    print("\n--- OpenModelica Simulation Batch Complete ---")

if __name__ == '__main__':
    import yaml
    print("Running modelica_runner.py in standalone mode for testing.")

    try:
        with open("../config/params.yaml", 'r') as f:
            test_config = yaml.safe_load(f)
        run_modelica_simulations(test_config)
    except FileNotFoundError:
        print("\n[Error] Could not find '../config/params.yaml'.")
        print("Please run this script from the 'src' directory or run the main.py from the root.")
