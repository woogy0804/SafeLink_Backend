from features.feature_extractor import extract_feature_dict


def extract_features(url: str) -> dict:
    return extract_feature_dict(url)
