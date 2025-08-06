from OMPython import OMCSessionZMQ, ModelicaSystem, compile_fmu
import yaml, os

with open("params.yaml") as f: cfg = yaml.safe_load(f)
for m_id, m in cfg["motors"].items():
    for f_kHz in cfg["hil_freq_kHz"]:
        for ctrl in cfg["controller"]:
            csv = f"results/{m_id}_nominal.csv"  # 대표 케이스 선택
            os.system(f"sed -e 's/<replace>/{m_id}_nominal/' "
                      f"-e 's/%controller%/{ctrl}/' "
                      f"-e 's/hil_kHz/{f_kHz}/' "
                      f"BLDC_System.mo > tmp.mo")
            omc = OMCSessionZMQ(); omc.sendExpression('loadFile("tmp.mo")')
            omc.sendExpression('simulate(EccentricityStudy.BLDC_System, '
                               'startTime=0, stopTime=5, outputFormat="csv")')
