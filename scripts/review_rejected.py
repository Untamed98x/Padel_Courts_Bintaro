import argparse
import pandas as pd
import shutil
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]  # padel_bintaro/
OUT = ROOT / "output"
PADEL_FILE = OUT / "padel_bintaro.csv"
REJ_FILE = OUT / "rejected_places.csv"
EXPORT_REVIEW = OUT / "rejected_places_for_review.csv"

def backup(path: Path):
    if path.exists():
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        bak = path.with_suffix(f".bak.{ts}.csv")
        shutil.copy2(path, bak)

def safe_read_csv(path: Path):
    return pd.read_csv(path) if path.exists() else pd.DataFrame()

def normalize_key(row):
    pid = str(row.get("place_id", "")).strip()
    name = str(row.get("name", "")).strip().lower()
    lat = round(float(row.get("lat", 0) or 0), 5)
    lon = round(float(row.get("lon", 0) or 0), 5)
    return f"{pid}|{name}|{lat}|{lon}"

def list_sample(df, idx):
    if idx not in df.index:
        return f"[error] Index {idx} not in dataframe"
    cols = [c for c in ["place_id","name","lat","lon","rating","review_count","reason"] if c in df.columns]
    row = df.loc[idx, cols].to_dict()
    return "\n".join(f"{k}: {v}" for k, v in row.items())

def process_approvals(rej_df: pd.DataFrame, approved_idx: list[int]):
    if not approved_idx:
        print("[info] Tidak ada yang di-approve.")
        return 0, 0

    # intersect indexes to current rej_df to avoid KeyError
    approved_idx = [i for i in approved_idx if i in rej_df.index]
    if not approved_idx:
        print("[warn] Tidak ada indeks valid pada rejected_places.csv (mungkin file berubah).")
        return 0, 0

    approve_df = rej_df.loc[approved_idx].copy().reset_index(drop=True)

    # ensure essential columns
    for c in ["place_id","name","lat","lon"]:
        if c not in approve_df.columns:
            approve_df[c] = None

    # backup destination files
    backup(PADEL_FILE)
    backup(REJ_FILE)

    # load existing padel and build key set
    padel_df_existing = safe_read_csv(PADEL_FILE)
    if not padel_df_existing.empty:
        padel_df_existing["_key"] = padel_df_existing.apply(normalize_key, axis=1)
        padel_keys = set(padel_df_existing["_key"].tolist())
    else:
        padel_keys = set()

    approve_df["_key"] = approve_df.apply(normalize_key, axis=1)
    approve_df["__skip"] = approve_df["_key"].isin(padel_keys)

    kept = approve_df[~approve_df["__skip"]].drop(columns=["_key","__skip"])
    skipped = approve_df[approve_df["__skip"]]

    # append and dedupe
    if padel_df_existing.empty:
        new_padel = kept.copy()
    else:
        new_padel = pd.concat([padel_df_existing.drop(columns=["_key"], errors="ignore"), kept], ignore_index=True)

    if "place_id" in new_padel.columns and new_padel["place_id"].notna().any():
        new_padel = new_padel.drop_duplicates(subset=["place_id"], keep="first")
    else:
        new_padel = new_padel.drop_duplicates()

    new_padel.to_csv(PADEL_FILE, index=False, encoding="utf-8-sig")
    print(f"[saved] {PADEL_FILE.name} (+{len(kept)} added, {len(skipped)} skipped duplicates)")

    # remove approved rows from rejected original and save
    remaining = rej_df.drop(index=approved_idx).reset_index(drop=True)
    remaining.to_csv(REJ_FILE, index=False, encoding="utf-8-sig")
    print(f"[saved] {REJ_FILE.name} (remaining {len(remaining)})")

    if not skipped.empty:
        print("\nSkipped (duplicate detected):")
        print(skipped[["place_id","name","lat","lon"]].to_string(index=False))

    return len(kept), len(skipped)

def mode_export():
    rej_df = safe_read_csv(REJ_FILE)
    if rej_df.empty:
        print("[info] rejected_places.csv kosong atau tidak ada.")
        return
    df_reset = rej_df.reset_index().rename(columns={"index": "i"})
    df_reset["approve"] = ""  # user will fill with 1/yes
    df_reset.to_csv(EXPORT_REVIEW, index=False, encoding="utf-8-sig")
    print(f"[export] Tersimpan: {EXPORT_REVIEW}")

def mode_apply_exported():
    if not EXPORT_REVIEW.exists():
        print("[error] File export tidak ditemukan. Jalankan --export-first dulu.")
        return
    df = pd.read_csv(EXPORT_REVIEW)
    if "approve" not in df.columns or "i" not in df.columns:
        print("[error] File export invalid (butuh kolom 'i' dan 'approve').")
        return
    approved = df[df["approve"].astype(str).str.strip().str.lower().isin(["1","y","yes","true"])]["i"].astype(int).tolist()
    if not approved:
        print("[info] Tidak ada baris bertanda approve.")
        return
    rej_df = safe_read_csv(REJ_FILE)
    process_approvals(rej_df, approved)

def mode_interactive():
    rej_df = safe_read_csv(REJ_FILE)
    if rej_df.empty:
        print("[info] rejected_places.csv kosong atau tidak ada.")
        return

    idx_list = list(rej_df.index)
    to_approve = []
    i = 0
    total = len(idx_list)
    print(f"[interactive] {total} rows")

    while i < total:
        idx = idx_list[i]
        print("\n" + "-"*40)
        print(f"Index (file index): {idx}  [{i+1}/{total}]")
        print(list_sample(rej_df, idx))
        ans = input("\n(y) approve / (n) skip / (a) approve all remaining / (e) export remaining / (q) quit: ").strip().lower()
        if ans == "y":
            to_approve.append(idx)
            i += 1
        elif ans == "n" or ans == "":
            i += 1
        elif ans == "a":
            to_approve.extend(idx_list[i:])
            break
        elif ans == "e":
            # export remaining for external review
            remaining = rej_df.loc[idx_list[i:]].reset_index().rename(columns={"index": "i"})
            remaining["approve"] = ""
            remaining.to_csv(EXPORT_REVIEW, index=False, encoding="utf-8-sig")
            print(f"[export] Remaining exported to {EXPORT_REVIEW}. Edit 'approve' and run --apply-approved.")
            return
        elif ans == "q":
            break
        else:
            print("Pilihan tidak dikenali. Ketik y/n/a/e/q.")

    if to_approve:
        print(f"\nAkan approve {len(to_approve)} rows: {to_approve}")
        if input("Lanjutkan proses (y/n)? ").strip().lower() == "y":
            process_approvals(rej_df, to_approve)
        else:
            print("Dibatalkan.")
    else:
        print("Tidak ada yang dipilih untuk di-approve.")

def main():
    p = argparse.ArgumentParser(description="Review & move rows from rejected_places.csv to padel_bintaro.csv")
    p.add_argument("--export-first", action="store_true", help="Export rejected to CSV for manual review (adds 'approve' col).")
    p.add_argument("--apply-approved", action="store_true", help="Apply approvals from the exported CSV (rejected_places_for_review.csv).")
    p.add_argument("--interactive", action="store_true", help="Interactive per-row approve (default).")
    args = p.parse_args()

    if args.export_first:
        mode_export(); return
    if args.apply_approved:
        mode_apply_exported(); return
    mode_interactive()

if __name__ == "__main__":
    main()