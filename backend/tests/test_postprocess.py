"""Tests for postprocessing functionality."""

import pytest
from app.postprocess import _norm_text, _lemmas, _dedup, _is_garbage, postprocess_expanded


def test_norm_text():
    """Test text normalization."""
    assert _norm_text("  Ремонт    окон  ПВХ  ") == "ремонт окон пвх"
    assert _norm_text("УСТАНОВКА ОКОН") == "установка окон"
    assert _norm_text("") == ""


def test_lemmas():
    """Test lemmatization."""
    result = _lemmas("ремонт пластиковых окон")
    assert "ремонт" in result
    assert "пластиковый" in result or "пластик" in result
    assert "окно" in result


def test_is_garbage():
    """Test garbage detection."""
    # Too short
    assert _is_garbage("окна") == True
    
    # Too long
    assert _is_garbage("очень длинный запрос с множеством слов который превышает лимит") == True
    
    # Good length
    assert _is_garbage("ремонт пластиковых окон") == False
    
    # Duplicate words
    assert _is_garbage("купить купить окна") == True
    assert _is_garbage("бесплатно бесплатно установка") == True


def test_dedup():
    """Test deduplication."""
    queries = [
        "ремонт окон",
        "ремонт окон пвх",
        "ремонт окон",  # exact duplicate
        "ремонт пластиковых окон",  # similar but different
        "окон ремонт",  # different order
    ]
    
    result = _dedup(queries)
    
    # Should remove exact duplicates
    assert result.count("ремонт окон") == 1
    
    # Should keep different variations
    assert "ремонт окон пвх" in result
    assert "ремонт пластиковых окон" in result


def test_postprocess_expanded():
    """Test full postprocessing pipeline."""
    test_data = {
        "topic": "ремонт окон",
        "locale": "ru-RU",
        "expanded": [
            {
                "cluster_id": "1",
                "cluster_name": "Ремонт",
                "queries": [
                    {"q": "ремонт окон", "intent": "commercial"},
                    {"q": "ремонт окон пвх", "intent": "commercial"},
                    {"q": "ремонт", "intent": "commercial"},  # too short, should be filtered
                    {"q": "ремонт окон", "intent": "commercial"},  # duplicate
                ]
            },
            {
                "cluster_id": "2", 
                "cluster_name": "Установка",
                "queries": [
                    {"q": "установка пластиковых окон", "intent": "service"},
                    {"q": "", "intent": "service"},  # empty, should be filtered
                ]
            }
        ]
    }
    
    result = postprocess_expanded(test_data, max_total=100)
    
    # Check structure is preserved
    assert "expanded" in result
    assert len(result["expanded"]) <= 2
    
    # Check filtering worked
    all_queries = []
    for cluster in result["expanded"]:
        for query in cluster["queries"]:
            all_queries.append(query["q"])
    
    # Should not contain garbage
    assert "ремонт" not in all_queries  # too short
    assert "" not in all_queries  # empty
    
    # Should contain good queries
    assert "ремонт окон" in all_queries
    assert "установка пластиковых окон" in all_queries
