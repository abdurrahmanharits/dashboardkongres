import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
import pandas as pd
import streamlit as st
from pathlib import Path
import math

st.set_page_config(page_title="Dashboard Pemenangan PB HMI", layout="wide")

DB_DIR = Path("db")
KANDIDAT_FILE = DB_DIR / "matriks_kandidat.csv"
BADKO_FILE = DB_DIR / "matriks_badko.csv"
BADKO_MASTER_FILE = DB_DIR / "matriks_badko_master.csv"
LEGACY_KANDIDAT_FILE = Path("matriks_kandidat.csv")
LEGACY_BADKO_FILE = Path("matriks_badko.csv")
PESERTA_XLSX_FILE = DB_DIR / "lampiran_II_peserta_kongres_hmi.xlsx"

KANDIDAT_COLS = [
    "Nama Kandidat",
    "Nomor HP Kandidat",
    "Asal Cabang",
    "Mentor",
    "Jumlah Cabang Pendukung",
]

BADKO_COLS = [
    "Nama Cabang",
    "Badko",
    "Ketua Cabang",
    "Mentor",
    "Nomor Mentor",
    "Stance Politik",
]

BADKO_MASTER_COLS = [
    "Nama Badko",
    "Jumlah Cabang",
    "Nama Ketua Badko",
    "Nomor HP",
]


def load_csv(path: Path, columns: list[str]) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=columns)

    try:
        df = pd.read_csv(path)
    except Exception:
        return pd.DataFrame(columns=columns)

    for col in columns:
        if col not in df.columns:
            df[col] = ""

    return df[columns].copy()


def normalize_badko_detail(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(columns=BADKO_COLS)
    mapping = {
        "Nama Cabang": ["Nama Cabang", "Sebaran Badko"],
        "Badko": ["Badko", "BADKO", "Matriks Badko"],
        "Ketua Cabang": ["Ketua Cabang", "Nama Ketum Cabang"],
        "Mentor": ["Mentor"],
        "Nomor Mentor": ["Nomor Mentor", "Nomor Telfon"],
        "Stance Politik": ["Stance Politik"],
    }

    for target, candidates in mapping.items():
        source = next((col for col in candidates if col in df.columns), None)
        out[target] = df[source] if source else ""

    out = out.fillna("")
    out["Badko"] = out["Badko"].astype(str).str.strip().str.title()
    out["Ketua Cabang"] = out["Ketua Cabang"].astype(str).str.strip()
    out.loc[out["Ketua Cabang"].str.fullmatch(r"\d+(\.0+)?"), "Ketua Cabang"] = ""
    out["Nomor Mentor"] = out["Nomor Mentor"].astype(str).replace({"None": "", "nan": ""})
    return out


def load_kandidat_data() -> pd.DataFrame:
    if KANDIDAT_FILE.exists():
        try:
            return normalize_kandidat(pd.read_csv(KANDIDAT_FILE))
        except Exception:
            return pd.DataFrame(columns=KANDIDAT_COLS)
    if LEGACY_KANDIDAT_FILE.exists():
        try:
            return normalize_kandidat(pd.read_csv(LEGACY_KANDIDAT_FILE))
        except Exception:
            return pd.DataFrame(columns=KANDIDAT_COLS)
    return pd.DataFrame(columns=KANDIDAT_COLS)


def badko_from_excel(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame(columns=BADKO_COLS)

    try:
        raw = pd.read_excel(path, sheet_name="Data")
    except Exception as exc:
        st.warning(f"Gagal membaca database Excel BADKO: {exc}")
        return pd.DataFrame(columns=BADKO_COLS)

    out = pd.DataFrame(columns=BADKO_COLS)
    out["Nama Cabang"] = raw.get("Cabang", "")
    out["Badko"] = raw.get("Badan Koordinasi", "")
    out["Ketua Cabang"] = ""
    out["Mentor"] = ""
    out["Nomor Mentor"] = ""
    out["Stance Politik"] = ""
    return out.fillna("")


def load_badko_data() -> pd.DataFrame:
    if BADKO_FILE.exists():
        try:
            return normalize_badko_detail(pd.read_csv(BADKO_FILE))
        except Exception:
            return pd.DataFrame(columns=BADKO_COLS)
    if PESERTA_XLSX_FILE.exists():
        df = badko_from_excel(PESERTA_XLSX_FILE)
        if not df.empty:
            save_csv(df, BADKO_FILE)
        return df
    if LEGACY_BADKO_FILE.exists():
        try:
            return normalize_badko_detail(pd.read_csv(LEGACY_BADKO_FILE))
        except Exception:
            return pd.DataFrame(columns=BADKO_COLS)
    return pd.DataFrame(columns=BADKO_COLS)


def clean_kandidat(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Jumlah Cabang Pendukung"] = pd.to_numeric(
        out["Jumlah Cabang Pendukung"], errors="coerce"
    ).fillna(0).astype(int)
    return out


def normalize_kandidat(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame(columns=KANDIDAT_COLS)
    out["Nama Kandidat"] = (
        df["Nama Kandidat"]
        if "Nama Kandidat" in df.columns
        else (df["Kelompok"] if "Kelompok" in df.columns else "")
    )
    out["Nomor HP Kandidat"] = (
        df["Nomor HP Kandidat"] if "Nomor HP Kandidat" in df.columns else ""
    )
    out["Asal Cabang"] = df["Asal Cabang"] if "Asal Cabang" in df.columns else ""
    out["Mentor"] = df["Mentor"] if "Mentor" in df.columns else ""
    out["Jumlah Cabang Pendukung"] = (
        df["Jumlah Cabang Pendukung"] if "Jumlah Cabang Pendukung" in df.columns else 0
    )
    return clean_kandidat(out.fillna(""))


def build_badko_master(detail_df: pd.DataFrame, existing_master: pd.DataFrame | None = None) -> pd.DataFrame:
    base = detail_df.copy()
    base["Badko"] = base["Badko"].fillna("").astype(str).str.strip().str.title()
    base["Nama Cabang"] = base["Nama Cabang"].fillna("").astype(str).str.strip()
    base = base[base["Badko"] != ""]

    summary = (
        base.groupby("Badko", as_index=False)["Nama Cabang"]
        .count()
        .rename(columns={"Badko": "Nama Badko", "Nama Cabang": "Jumlah Cabang"})
    )

    if existing_master is None or existing_master.empty:
        summary["Nama Ketua Badko"] = ""
        summary["Nomor HP"] = ""
        return summary[BADKO_MASTER_COLS]

    master = existing_master.copy()
    for col in BADKO_MASTER_COLS:
        if col not in master.columns:
            master[col] = ""
    master["Nama Badko"] = master["Nama Badko"].fillna("").astype(str).str.strip()
    master = master[master["Nama Badko"] != ""].drop_duplicates(subset=["Nama Badko"], keep="last")

    out = summary.merge(master[["Nama Badko", "Nama Ketua Badko", "Nomor HP"]], on="Nama Badko", how="left")
    out["Nama Ketua Badko"] = out["Nama Ketua Badko"].fillna("")
    out["Nomor HP"] = out["Nomor HP"].fillna("")
    return out[BADKO_MASTER_COLS]


def load_badko_master(detail_df: pd.DataFrame) -> pd.DataFrame:
    existing = load_csv(BADKO_MASTER_FILE, BADKO_MASTER_COLS)
    return build_badko_master(detail_df, existing)


def save_badko_master(df: pd.DataFrame, detail_df: pd.DataFrame) -> None:
    out = df.copy()
    for col in BADKO_MASTER_COLS:
        if col not in out.columns:
            out[col] = ""
    out["Nama Badko"] = out["Nama Badko"].fillna("").astype(str).str.strip()
    out = out[out["Nama Badko"] != ""].drop_duplicates(subset=["Nama Badko"], keep="last")
    out = build_badko_master(
        detail_df,
        out[["Nama Badko", "Jumlah Cabang", "Nama Ketua Badko", "Nomor HP"]],
    )
    save_csv(out, BADKO_MASTER_FILE)


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False)


st.title("Dashboard Pemenangan Kandidat PB HMI")

save_notice = st.session_state.pop("save_notice", None)
if save_notice:
    st.success(save_notice)

kandidat_df = clean_kandidat(load_kandidat_data())
badko_df = load_badko_data()
badko_master_df = load_badko_master(badko_df)

# Ringkasan utama
total_entitas_kandidat = int(
    kandidat_df["Nama Kandidat"]
    .fillna("")
    .astype(str)
    .str.strip()
    .replace("None", "")
    .loc[lambda s: s != ""]
    .nunique()
)
total_cabang = int(
    badko_df["Nama Cabang"]
    .fillna("")
    .astype(str)
    .str.strip()
    .replace("None", "")
    .loc[lambda s: s != ""]
    .nunique()
)
total_badko = int(
    badko_df["Badko"]
    .fillna("")
    .astype(str)
    .str.strip()
    .replace("None", "")
    .loc[lambda s: s != ""]
    .nunique()
)
with st.container(border=True):
    st.subheader("Overview Kongres")

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Kandidat", total_entitas_kandidat)
    col2.metric("Total Badko", total_badko)
    col3.metric("Total Cabang", total_cabang)

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Sebaran Dukungan")
    if kandidat_df.empty:
        st.info("Data kandidat masih kosong.")
    else:
        dukungan_kandidat = (
            kandidat_df.groupby("Nama Kandidat", as_index=False)["Jumlah Cabang Pendukung"].sum()
        )
        dukungan_kandidat = dukungan_kandidat[
            dukungan_kandidat["Nama Kandidat"].fillna("").astype(str).str.strip() != ""
        ]
        if dukungan_kandidat.empty:
            st.info("Nama kandidat belum terisi.")
        else:
            total_dukungan = dukungan_kandidat["Jumlah Cabang Pendukung"].sum()
            dukungan_kandidat["Persentase"] = (
                dukungan_kandidat["Jumlah Cabang Pendukung"] / total_dukungan * 100
            ).round(1)
            labels = dukungan_kandidat.apply(
                lambda r: f"{r['Nama Kandidat']}\n{int(r['Jumlah Cabang Pendukung'])} ({r['Persentase']:.1f}%)",
                axis=1,
            ).tolist()
            values = dukungan_kandidat["Jumlah Cabang Pendukung"].tolist()

            fig, ax = plt.subplots(figsize=(9, 6), dpi=130)
            colors = plt.cm.tab20.colors[: len(values)]
            wedges, _ = ax.pie(
                values,
                colors=colors,
                startangle=90,
            )

            total = sum(values) if values else 1
            small_idx = 0
            for i, (wedge, label, val) in enumerate(zip(wedges, labels, values)):
                frac = val / total
                angle = (wedge.theta1 + wedge.theta2) / 2.0
                rad = math.radians(angle)

                r = 0.62
                if frac < 0.18:
                    r = 0.78 if small_idx % 2 == 0 else 0.48
                    small_idx += 1

                x = r * math.cos(rad)
                y = r * math.sin(rad)
                txt = ax.text(
                    x,
                    y,
                    label,
                    ha="center",
                    va="center",
                    fontsize=10,
                    fontweight="bold",
                    color="white",
                )
                txt.set_path_effects([pe.withStroke(linewidth=1.8, foreground="black")])

            ax.axis("equal")
            st.pyplot(fig, use_container_width=True)
            plt.close(fig)

with right:
    st.subheader("Top 5 Kandidat")
    if kandidat_df.empty:
        st.info("Data kandidat masih kosong.")
    else:
        kandidat_rank = kandidat_df.copy()
        kandidat_rank["Nama Kandidat"] = kandidat_rank["Nama Kandidat"].fillna("").astype(str).str.strip()
        kandidat_rank["Mentor"] = kandidat_rank["Mentor"].fillna("").astype(str).str.strip()
        kandidat_rank["Asal Cabang"] = kandidat_rank["Asal Cabang"].fillna("").astype(str).str.strip()
        kandidat_rank = kandidat_rank[kandidat_rank["Nama Kandidat"] != ""]

        top5 = (
            kandidat_rank.groupby("Nama Kandidat", as_index=False)
            .agg(
                {
                    "Jumlah Cabang Pendukung": "sum",
                    "Mentor": lambda s: ", ".join(sorted(set(v for v in s if v))),
                    "Asal Cabang": lambda s: ", ".join(sorted(set(v for v in s if v))),
                }
            )
            .rename(
                columns={
                    "Jumlah Cabang Pendukung": "Total Cabang Pendukung",
                    "Asal Cabang": "List Cabang Pendukung",
                }
            )
            .sort_values("Total Cabang Pendukung", ascending=False)
            .head(5)
            .reset_index(drop=True)
        )
        st.dataframe(top5, use_container_width=True, hide_index=True)

st.divider()

st.subheader("Editor Tabel Dinamis")
st.write(
    "Gunakan editor di bawah untuk menambah/mengubah data. "
    "Untuk menghapus baris, centang kolom `Hapus`, lalu klik tombol simpan."
)

# Editor Kandidat
st.markdown("Matriks Kandidat")
editable_kandidat = kandidat_df.copy()
editable_kandidat["Hapus"] = False

edited_kandidat = st.data_editor(
    editable_kandidat,
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    column_config={
        "Jumlah Cabang Pendukung": st.column_config.NumberColumn(
            "Jumlah Cabang Pendukung",
            min_value=0,
            step=1,
            format="%d",
        ),
        "Hapus": st.column_config.CheckboxColumn("Hapus"),
    },
    key="editor_kandidat",
)

if st.button("Simpan Matriks Kandidat", type="primary"):
    to_save = edited_kandidat[edited_kandidat["Hapus"] != True].drop(columns=["Hapus"])
    to_save = clean_kandidat(to_save)
    save_csv(to_save, KANDIDAT_FILE)
    st.session_state["save_notice"] = "Matriks kandidat berhasil disimpan. Overview dan grafik diperbarui."
    st.rerun()

st.divider()

# Editor BADKO
st.markdown("Matriks BADKO")
st.markdown("Tabel Badko")
editable_badko_master = badko_master_df.copy()

edited_badko_master = st.data_editor(
    editable_badko_master,
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    column_config={
        "Jumlah Cabang": st.column_config.NumberColumn(
            "Jumlah Cabang",
            min_value=0,
            step=1,
            format="%d",
        ),
    },
    disabled=["Jumlah Cabang"],
    key="editor_badko_master",
)

if st.button("Simpan Tabel BADKO", type="primary"):
    save_badko_master(edited_badko_master, badko_df)
    st.session_state["save_notice"] = "Tabel BADKO berhasil disimpan. Overview dan grafik diperbarui."
    st.rerun()

st.markdown("#### Tabel Cabang")
editable_badko = badko_df.copy()
editable_badko["Hapus"] = False

edited_badko = st.data_editor(
    editable_badko,
    num_rows="dynamic",
    hide_index=True,
    use_container_width=True,
    column_config={
        "Hapus": st.column_config.CheckboxColumn("Hapus"),
    },
    key="editor_badko_detail",
)

if st.button("Simpan Tabel Cabang BADKO", type="primary"):
    to_save = edited_badko[edited_badko["Hapus"] != True].drop(columns=["Hapus"])
    save_csv(to_save, BADKO_FILE)
    st.session_state["save_notice"] = "Tabel Cabang BADKO berhasil disimpan. Overview dan grafik diperbarui."
    st.rerun()
