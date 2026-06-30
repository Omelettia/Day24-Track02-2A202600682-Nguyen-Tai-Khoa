# tests/test_vault.py
import base64
import pandas as pd
from src.encryption.vault import SimpleVault


def test_round_trip(tmp_path):
    v = SimpleVault(master_key_path=str(tmp_path / ".vault_key"))
    original = "Nguyen Van A - CCCD: 012345678901"
    enc = v.encrypt_data(original)
    assert enc["algorithm"] == "AES-256-GCM"
    # ciphertext must not contain the plaintext
    assert original not in enc["ciphertext"]
    assert v.decrypt_data(enc) == original


def test_kek_persisted_as_32_bytes(tmp_path):
    p = tmp_path / ".vault_key"
    SimpleVault(master_key_path=str(p))
    raw = p.read_bytes()
    assert len(base64.b64decode(raw)) == 32  # 256-bit key


def test_kek_reused_across_instances(tmp_path):
    p = str(tmp_path / ".vault_key")
    v1 = SimpleVault(master_key_path=p)
    enc = v1.encrypt_data("secret-value")
    v2 = SimpleVault(master_key_path=p)  # reloads same KEK from file
    assert v2.decrypt_data(enc) == "secret-value"


def test_ciphertext_nondeterministic(tmp_path):
    v = SimpleVault(master_key_path=str(tmp_path / ".vault_key"))
    a = v.encrypt_data("x")
    b = v.encrypt_data("x")
    assert a["ciphertext"] != b["ciphertext"]  # random nonce + fresh DEK each call


def test_encrypt_column(tmp_path):
    v = SimpleVault(master_key_path=str(tmp_path / ".vault_key"))
    df = pd.DataFrame({"cccd": ["012345678901", "987654321098"], "benh": ["A", "B"]})
    enc_df = v.encrypt_column(df, "cccd")
    assert "012345678901" not in enc_df["cccd"].iloc[0]
    assert enc_df["benh"].tolist() == ["A", "B"]  # other column untouched
