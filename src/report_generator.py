import os
import subprocess
import glob
from typing import Dict, Any

def generate_reports(config: Dict[str, Any]):
    """
    Generates a PDF report for each motor using a Markdown template and Pandoc.
    """
    print("\n--- Starting Report Generation ---")

    paths = config['paths']

    # Ensure Pandoc is installed
    try:
        subprocess.run(['pandoc', '--version'], check=True, capture_output=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("\n[Error] Pandoc not found. Please install Pandoc and ensure it is in your system's PATH.")
        print("Skipping report generation.")
        return

    # Check for report template
    template_path = paths['report_template']
    if not os.path.exists(template_path):
        print(f"[Error] Report template not found at '{template_path}'. Skipping.")
        return

    with open(template_path, 'r', encoding='utf-8') as f:
        md_template = f.read()

    os.makedirs(paths['report'], exist_ok=True)

    for motor_id, motor_params in config['motors'].items():
        print(f"\nGenerating report for motor: {motor_id}")

        # --- Find the generated plots ---
        # Note: These paths must match the output names from post_processor.py
        ripple_plot = os.path.join(paths['figs'], f"{motor_id}_femm_ripple.png")

        # Find a representative system plot
        # We'll just take the first one we find for this motor for the report
        system_plots = glob.glob(os.path.join(paths['figs'], f"{motor_id}_*_response.png"))
        system_plot = system_plots[0] if system_plots else ""

        campbell_plot = os.path.join(paths['figs'], f"{motor_id}_campbell_placeholder.png")

        # Check if plots exist, use placeholder text if not
        if not os.path.exists(ripple_plot):
            print(f"  [Warning] Ripple plot not found at {ripple_plot}")
        if not os.path.exists(system_plot):
            print(f"  [Warning] System response plot not found.")
        if not os.path.exists(campbell_plot):
            print(f"  [Warning] Campbell placeholder not found at {campbell_plot}")

        # --- Populate Template ---
        report_content = md_template.format(
            motor_id=motor_id,
            ripple_plot_path=os.path.join('..', ripple_plot).replace('\\', '/'),
            system_response_plot_path=os.path.join('..', system_plot).replace('\\', '/') if system_plot else "",
            campbell_plot_path=os.path.join('..', campbell_plot).replace('\\', '/'),
            **motor_params
        )

        # --- Save temporary Markdown and convert to PDF ---
        temp_md_path = os.path.join(paths['report'], f"temp_{motor_id}_report.md")
        with open(temp_md_path, 'w', encoding='utf-8') as f:
            f.write(report_content)

        output_pdf_path = os.path.join(paths['report'], f"{motor_id}_Eccentricity_Study.pdf")

        try:
            # Pandoc command
            # We add --from=markdown+yaml_metadata_block to handle potential metadata in the future
            # The --standalone flag ensures it's a complete document.
            cmd = [
                'pandoc', temp_md_path,
                '--from', 'markdown',
                '--standalone',
                '-o', output_pdf_path
            ]
            subprocess.run(cmd, check=True, capture_output=True, text=True)
            print(f"  -> Successfully created PDF report: {output_pdf_path}")
        except subprocess.CalledProcessError as e:
            print(f"  [Error] Pandoc failed to generate PDF for {motor_id}.")
            print(f"  Pandoc stderr: {e.stderr}")
        finally:
            # Clean up the temporary markdown file
            if os.path.exists(temp_md_path):
                os.remove(temp_md_path)

    print("\n--- Report Generation Complete ---")


if __name__ == '__main__':
    import yaml
    import glob # Added for standalone test
    print("Running report_generator.py in standalone mode for testing.")

    try:
        with open("../config/params.yaml", 'r') as f:
            test_config = yaml.safe_load(f)
        generate_reports(test_config)
    except FileNotFoundError:
        print("\n[Error] Could not find '../config/params.yaml'.")
        print("Please run this script from the 'src' directory or run the main.py from the root.")
