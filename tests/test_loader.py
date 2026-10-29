import pytest
from MDAnalysisTests import datafiles as D

from mdscope import loader, registry


def test_load_pdb_summary():
    s = loader.load(D.PDB_small)
    info = loader.summarize(s)
    assert info["n_frames"] == 1
    assert info["n_atoms"] == s.universe.atoms.n_atoms
    assert info["chains"] and info["chains"][0]["n_residues"] > 100
    assert registry.get(s.system_id) is s


def test_load_gro_xtc_counts_frames():
    s = loader.load(D.GRO, D.XTC)
    info = loader.summarize(s)
    assert info["n_frames"] == 10
    assert info["dt_ps"] is not None
    assert info["n_water_residues"] > 0


def test_same_files_same_id():
    a = loader.load(D.PDB_small)
    b = loader.load(D.PDB_small)
    assert a.system_id == b.system_id


def test_unknown_id_lists_known():
    loader.load(D.PDB_small, name="adk")
    with pytest.raises(KeyError, match="adk"):
        registry.get("nope")


def test_missing_file():
    with pytest.raises(FileNotFoundError):
        loader.load(str(D.PDB_small) + ".missing")
