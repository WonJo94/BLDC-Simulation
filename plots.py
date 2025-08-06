import pandas as pd, numpy as np, matplotlib.pyplot as plt, glob

def ripple(csv):
    T = pd.read_csv(csv)["torque_Nm"]; return (T.max()-T.min())/T.mean()*100

for m_id in ["ILM25x08","ILM50x14"]:
    files = glob.glob(f"results/{m_id}_*.csv")
    labels = [os.path.basename(f)[len(m_id)+1:-4] for f in files]
    vals   = [ripple(f) for f in files]
    plt.figure(); plt.bar(labels, vals)
    plt.ylabel("Ripple [%]"); plt.xticks(rotation=70)
    plt.tight_layout(); plt.savefig(f"figs/{m_id}_ripple.png")
