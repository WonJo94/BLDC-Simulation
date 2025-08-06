import femm, numpy as np, pandas as pd, yaml, os, itertools as it

with open("params.yaml") as f: cfg = yaml.safe_load(f)
geom_err = cfg["geometry_errors"]

def femm_torque_map(dxf, motor, case):
    femm.openfemm(); femm.opendocument(dxf)
    # --- 편심·틂 적용 ---
    femm.mi_seteditmode("group"); femm.mi_setgroup("Rotor")
    femm.mi_movetranslate(case["static_ecc"], 0)
    if case["tilt_deg"]:
        ang = np.radians(case["tilt_deg"])
        femm.mi_mirror(0, 0, np.tan(ang))
    # --- 스윕 ---
    mech_span = 360 / (motor["poles"]/2)
    thetas, torques = [], []
    for mech_deg in np.arange(0, mech_span, cfg["step_deg"]):
        femm.mi_modifygrow("group","rotate", mech_deg)
        femm.mi_analyze(); femm.mi_loadsolution()
        torques.append(femm.mo_gapintegral("Torque",0))
        thetas.append(mech_deg)
    femm.closefemm()
    return thetas, torques

def batch_all():
    for m_id, m in cfg["motors"].items():
        dxf = f"cad/{m_id}.dxf"            # 해당 단면 준비 필수
        for comb in it.product(geom_err["static_ecc"],
                               geom_err["dynamic_ecc"],
                               geom_err["tilt_deg"]):
            case = {"static_ecc":comb[0], "dynamic_ecc":comb[1],
                    "tilt_deg":comb[2]}
            θ,T = femm_torque_map(dxf, m, case)
            fn = f"results/{m_id}_{comb[0]}_{comb[1]}_{comb[2]}.csv"
            pd.DataFrame({"theta_deg":θ, "torque_Nm":T}).to_csv(fn,index=False)

if __name__=="__main__": batch_all()
