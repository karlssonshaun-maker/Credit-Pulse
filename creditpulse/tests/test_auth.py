from creditpulse.api.middleware.auth import generate_api_key, hash_api_key


def test_generate_api_key_returns_raw_prefix_and_hash():
    raw, prefix, digest = generate_api_key()
    assert raw.startswith("cp_")
    assert len(prefix) == 10
    assert len(digest) == 64
    assert hash_api_key(raw) == digest


def test_different_keys_have_different_hashes():
    raw1, _, digest1 = generate_api_key()
    raw2, _, digest2 = generate_api_key()
    assert raw1 != raw2
    assert digest1 != digest2
