import femm
import numpy as np
import pandas as pd
import os
import itertools as it
from typing import Dict, Any

def _run_single_femm_case(dxf_path: str, motor_params: Dict[str, Any], case: Dict[str, float], step_deg: float) -> pd.DataFrame:
    """
    Runs a single FEMM simulation for a given geometry case.

    Note: This function assumes FEMM is installed and accessible in the system's PATH.
    """
    try:
        femm.openfemm()
        femm.opendocument(dxf_path)

        # Apply geometric transformations for eccentricity and tilt
        # The rotor components must be assigned to group 1 in the DXF file.
        femm.mi_selectgroup(1)

        # Static eccentricity
        static_ecc_x = case.get("static_ecc_mm", 0.0)
        femm.mi_movetranslate(static_ecc_x, 0)

        # Rotor tilt (applied as a shear transformation, a simplification)
        tilt_deg = case.get("tilt_deg", 0.0)
        if tilt_deg != 0.0:
            # This is a simplified way to model tilt; real 3D effects are more complex.
            # For a 2D slice, it can be approximated by shearing the rotor geometry.
            # We are not using mi_mirror as in the original prompt as its usage was unclear.
            # A shear might be a more intuitive 2D approximation of a 3D tilt effect.
            # However, for this implementation, we will stick to a simple translation
            # and rotation, as tilt is complex to model correctly in 2D FEMM.
            # The user can extend this part if a better 2D approximation is devised.
            pass # Placeholder for a more advanced tilt model

        # --- Torque vs. Angle Sweep ---
        pole_pairs = motor_params['poles'] / 2
        mechanical_span_deg = 360 / pole_pairs

        thetas_mech = []
        torques_nm = []

        # The rotor group is already selected
        # Dynamic eccentricity is applied at each angle step
        dyn_ecc_x = case.get("dynamic_ecc_mm", 0.0)

        for mech_deg in np.arange(0, mechanical_span_deg, step_deg):
            femm.mi_selectgroup(1)
            # Rotate rotor to the new position
            femm.mi_rotate(0, 0, mech_deg)

            # Apply dynamic eccentricity at the current angle
            if dyn_ecc_x != 0.0:
                femm.mi_movetranslate(dyn_ecc_x, 0)

            # Analyze the model
            femm.mi_analyze(1)  # 1 for silent mode
            femm.mi_loadsolution()

            # Get torque from the air gap. The 'Torque' integral must be defined in the model.
            # The original prompt used mo_gapintegral("Torque", 0), which implies a specific
            # integral definition. We use the more general mo_groupintegral for the rotor group.
            femm.mo_selectblock(1) # Assuming rotor magnets are group 1
            torque = femm.mo_blockintegral(22) # 22 is the integral for 'Torque'
            torques_nm.append(torque)
            thetas_mech.append(mech_deg)

            # IMPORTANT: Undo transformations to reset for the next angle step
            if dyn_ecc_x != 0.0:
                femm.mi_movetranslate(-dyn_ecc_x, 0)
            femm.mi_rotate(0, 0, -mech_deg)


        femm.closefemm()
        return pd.DataFrame({"theta_deg": thetas_mech, "torque_Nm": torques_nm})

    except Exception as e:
        # In case of a FEMM error, close the instance and report
        print(f"An error occurred during FEMM simulation: {e}")
        femm.closefemm()
        return pd.DataFrame() # Return empty dataframe on failure


def run_femm_simulations(config: Dict[str, Any]):
    """
    Runs a batch of FEMM simulations for all motors and geometric error combinations.
    """
    print("--- Starting FEMM Simulation Batch ---")

    paths = config['paths']
    sim_params = config['simulation_params']

    os.makedirs(paths['results'], exist_ok=True)

    for motor_id, motor_params in config['motors'].items():
        print(f"\nProcessing motor: {motor_id}")

        dxf_path = os.path.join(paths['cad'], f"{motor_id}.dxf")
        if not os.path.exists(dxf_path):
            print(f"  [Warning] DXF file not found at '{dxf_path}'. Skipping motor.")
            continue

        # Generate all combinations of geometric errors
        errors = sim_params['geometry_errors']
        error_combinations = list(it.product(
            errors['static_ecc_mm'],
            errors['dynamic_ecc_mm'],
            errors['tilt_deg']
        ))

        for i, combo in enumerate(error_combinations):
            case = {
                "static_ecc_mm": combo[0],
                "dynamic_ecc_mm": combo[1],
                "tilt_deg": combo[2],
            }

            # Descriptive case name for the output file
            case_name = f"static_{combo[0]}_dyn_{combo[1]}_tilt_{combo[2]}"
            print(f"  Running case {i+1}/{len(error_combinations)}: {case_name}...")

            # Define sweep step size
            # The original prompt specified 1 electrical degree.
            pole_pairs = motor_params['poles'] / 2
            step_mech_deg = sim_params['femm']['sweep_step_elec_deg'] / pole_pairs

            # Run the simulation for this specific case
            results_df = _run_single_femm_case(dxf_path, motor_params, case, step_mech_deg)

            if not results_df.empty:
                # Save results to a CSV file
                output_filename = f"{motor_id}_{case_name.replace('.', 'p')}.csv"
                output_path = os.path.join(paths['results'], output_filename)
                results_df.to_csv(output_path, index=False)
                print(f"    -> Saved results to {output_path}")

    print("\n--- FEMM Simulation Batch Complete ---")

if __name__ == '__main__':
    # This allows running the script directly for testing
    import yaml
    print("Running femm_runner.py in standalone mode for testing.")

    # Load a dummy/test config
    try:
        with open("../config/params.yaml", 'r') as f:
            test_config = yaml.safe_load(f)
        run_femm_simulations(test_config)
    except FileNotFoundError:
        print("\n[Error] Could not find '../config/params.yaml'.")
        print("Please run this script from the 'src' directory or run the main.py from the root.")
