def test_create_instance(artifact_dir, create_instance):
    assert (artifact_dir / 'wikiconfig.py').exists()
    assert (artifact_dir / 'intermap.txt').exists()
    assert (artifact_dir / 'wiki_local').exists()
