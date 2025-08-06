import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import os
import glob
from typing import Dict, Any

def _calculate_ripple(series: pd.Series) -> float:
    """Calculates ripple as (max - min) / mean * 100%."""
    if series.mean() == 0:
        return 0.0
    return (series.max() - series.min()) / series.mean() * 100

def _create_femm_ripple_plot(results_path: str, motor_id: str, output_path: str):
    """
    Generates a bar chart of torque ripple from FEMM results for a given motor.
    """
    print(f"  Generating FEMM torque ripple plot for {motor_id}...")

    # Find all FEMM result files for the motor
    femm_files = glob.glob(os.path.join(results_path, f"{motor_id}_static_*.csv"))
    if not femm_files:
        print(f"    [Info] No FEMM result files found for {motor_id}. Skipping plot.")
        return

    labels = []
    ripple_values = []

    for f in femm_files:
        try:
            df = pd.read_csv(f)
            if "torque_Nm" in df.columns and not df.empty:
                ripple = _calculate_ripple(df["torque_Nm"])
                ripple_values.append(ripple)

                # Create a clean label from the filename
                base_name = os.path.basename(f)
                label = base_name.replace(f"{motor_id}_", "").replace(".csv", "").replace("_", " ").replace("p", ".")
                labels.append(label)
        except Exception as e:
            print(f"    [Warning] Could not process file {f}: {e}")

    if not labels:
        print(f"    [Info] No valid data to plot for {motor_id}.")
        return

    plt.figure(figsize=(12, 7))
    plt.bar(labels, ripple_values)
    plt.ylabel("Torque Ripple [%]")
    plt.xlabel("Geometric Error Combination")
    plt.title(f"FEMM Torque Ripple Analysis for {motor_id}")
    plt.xticks(rotation=80, ha='right')
    plt.tight_layout()
    plt.savefig(output_path)
    plt.close()
    print(f"    -> Saved plot to {output_path}")
    return output_path


def _create_system_response_plot(results_path: str, case_name: str, output_path: str):
    """
    Generates a plot of key system variables from an OpenModelica simulation.
    """
    print(f"  Generating system response plot for {case_name}...")

    sim_file = os.path.join(results_path, f"{case_name}_res.csv")
    if not os.path.exists(sim_file):
        print(f"    [Info] Simulation result file not found: {sim_file}. Skipping.")
        return

    try:
        df = pd.read_csv(sim_file)
    except Exception as e:
        print(f"    [Warning] Could not read or process file {sim_file}: {e}")
        return

    # Identify columns to plot (these names depend on the Modelica model output)
    # The simplified .mo template only reliably outputs 'time' and 'load.w'.
    # The others are placeholders for a more complex model.
    plot_vars = {
        'Rotor Speed': ('time', 'load.w', 'rad/s'),
        'Motor Torque': ('time', 'm1.torque', 'Nm'), # Placeholder name, depends on a full motor model
        'Phase A Current': ('time', 'inv.i_a', 'A')     # Placeholder name, depends on a full inverter model
    }

    fig, axes = plt.subplots(len(plot_vars), 1, figsize=(12, 10), sharex=True)
    fig.suptitle(f"System Response: {case_name}", fontsize=16)

    for i, (title, (x_col, y_col, y_label)) in enumerate(plot_vars.items()):
        if x_col in df.columns and y_col in df.columns:
            axes[i].plot(df[x_col], df[y_col])
            axes[i].set_ylabel(y_label)
            axes[i].set_title(title)
            axes[i].grid(True)
        else:
            axes[i].text(0.5, 0.5, f"'{y_col}' not in results", ha='center', va='center')
            axes[i].set_title(title)

    axes[-1].set_xlabel("Time [s]")
    plt.tight_layout(rect=[0, 0.03, 1, 0.95])
    plt.savefig(output_path)
    plt.close()
    print(f"    -> Saved plot to {output_path}")
    return output_path

def _create_campbell_diagram_placeholder(output_path: str):
    """Creates a placeholder image for a Campbell diagram."""
    plt.figure(figsize=(8, 6))
    plt.text(0.5, 0.5, "Campbell Diagram\n(Requires run-up simulation\nand FFT post-processing)",
             ha='center', va='center', fontsize=14, style='italic',
             bbox=dict(boxstyle="round,pad=0.5", fc="aliceblue", ec="black"))
    plt.title("Campbell Diagram (Placeholder)")
    plt.xticks([])
    plt.yticks([])
    plt.savefig(output_path)
    plt.close()
    return output_path


def generate_plots(config: Dict[str, Any]):
    """
    Main function to generate all plots from simulation results.
    """
    print("\n--- Starting Post-Processing and Plot Generation ---")

    paths = config['paths']
    results_path = paths['results']
    figs_path = paths['figs']

    os.makedirs(figs_path, exist_ok=True)

    for motor_id in config['motors'].keys():
        print(f"\nProcessing motor: {motor_id}")

        # --- FEMM Ripple Plot ---
        ripple_plot_output_path = os.path.join(figs_path, f"{motor_id}_femm_ripple.png")
        _create_femm_ripple_plot(results_path, motor_id, ripple_plot_output_path)

        # --- System Response Plots ---
        # Find all system simulation results for this motor
        system_files = glob.glob(os.path.join(results_path, f"{motor_id}_*_res.csv"))
        if system_files:
            # For demonstration, plot the first case found. A real analysis might be more selective.
            first_case = os.path.basename(system_files[0]).replace("_res.csv", "")
            sys_plot_output_path = os.path.join(figs_path, f"{first_case}_response.png")
            _create_system_response_plot(results_path, first_case, sys_plot_output_path)
        else:
            print(f"  No system simulation results found for {motor_id}.")

        # --- Campbell Diagram Placeholder ---
        campbell_plot_output_path = os.path.join(figs_path, f"{motor_id}_campbell_placeholder.png")
        _create_campbell_diagram_placeholder(campbell_plot_output_path)

    print("\n--- Plot Generation Complete ---")

if __name__ == '__main__':
    import yaml
    print("Running post_processor.py in standalone mode for testing.")

    try:
        with open("../config/params.yaml", 'r') as f:
            test_config = yaml.safe_load(f)
        generate_plots(test_config)
    except FileNotFoundError:
        print("\n[Error] Could not find '../config/params.yaml'.")
        print("Please run this script from the 'src' directory or run the main.py from the root.")
