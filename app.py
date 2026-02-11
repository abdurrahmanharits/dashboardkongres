import pandas as pd
import streamlit as st
from pathlib import Path

st.set_page_config(page_title="Dashboard Pemenangan PB HMI", layout="wide")

KANDIDAT_FILE = Path("matriks_kandidat.csv")
BADKO_FILE = Path("matriks_badko.csv")

KANDIDAT_COLS = [
    "Kelompok",
    "Asal Cabang",
    "Mentor",
    "Jumlah Cabang Pendukung",
]

BADKO_COLS = [
    "Matriks Badko",
    "Sebaran Badko",
    "Nama Ketum Cabang",
    "Nomor Telfon",
    "Stance Politik",
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


def clean_kandidat(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out["Jumlah Cabang Pendukung"] = pd.to_numeric(
        out["Jumlah Cabang Pendukung"], errors="coerce"
    ).fillna(0).astype(int)
    return out


def save_csv(df: pd.DataFrame, path: Path) -> None:
    df.to_csv(path, index=False)


st.title("Dashboard Pemenangan Kandidat PB HMI")
st.caption("Data dinamis: tambah, edit, atau hapus baris sesuai situasi politik terbaru.")

kandidat_df = clean_kandidat(load_csv(KANDIDAT_FILE, KANDIDAT_COLS))
badko_df = load_csv(BADKO_FILE, BADKO_COLS)

# Ringkasan utama
col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Entitas Kandidat", len(kandidat_df))
col2.metric("Total Cabang Pendukung", int(kandidat_df["Jumlah Cabang Pendukung"].sum()))
col3.metric("Total BADKO", badko_df["Matriks Badko"].nunique())
col4.metric("Total Ketum Cabang", badko_df["Nama Ketum Cabang"].nunique())

st.divider()

left, right = st.columns(2)

with left:
    st.subheader("Sebaran Dukungan per Kelompok")
    if kandidat_df.empty:
        st.info("Data kandidat masih kosong.")
    else:
        dukungan_kelompok = (
            kandidat_df.groupby("Kelompok", as_index=False)["Jumlah Cabang Pendukung"].sum()
        )
        st.bar_chart(dukungan_kelompok, x="Kelompok", y="Jumlah Cabang Pendukung")

with right:
    st.subheader("Peta Stance Politik BADKO")
    if badko_df.empty:
        st.info("Data BADKO masih kosong.")
    else:
        stance_count = (
            badko_df["Stance Politik"]
            .fillna("Tidak Diketahui")
            .replace("", "Tidak Diketahui")
            .value_counts()
            .rename_axis("Stance Politik")
            .reset_index(name="Jumlah")
        )
        st.bar_chart(stance_count, x="Stance Politik", y="Jumlah")

st.divider()

st.subheader("Editor Tabel Dinamis")
st.write(
    "Gunakan editor di bawah untuk menambah/mengubah data. "
    "Untuk menghapus baris, centang kolom `Hapus`, lalu klik tombol simpan."
)

# Editor Kandidat
st.markdown("### 1) Matriks Kandidat")
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
    st.success("Matriks kandidat berhasil disimpan.")
    st.rerun()

st.divider()

# Editor BADKO
st.markdown("### 2) Matriks BADKO")
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
    key="editor_badko",
)

if st.button("Simpan Matriks BADKO", type="primary"):
    to_save = edited_badko[edited_badko["Hapus"] != True].drop(columns=["Hapus"])
    save_csv(to_save, BADKO_FILE)
    st.success("Matriks BADKO berhasil disimpan.")
    st.rerun()
