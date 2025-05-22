# Live2D Model

The `live2d_model.py` module defines the `Live2dModel` class, which is responsible for loading and managing information about a Live2D model. This class specifically handles the preparation of data related to the model's expressions and emotions, but it **does not** handle the actual transmission of this data to the frontend or server. Its primary role is to provide a structured representation of the Live2D model's capabilities and current state regarding expressions.

## Classes

### `Live2dModel`
A class to represent a Live2D model, managing its information, emotion mappings, and providing utilities to extract and process emotion-related data from text.

#### Attributes:
*   `model_dict_path` (`str`): The path to the JSON file containing the model dictionary, which lists available Live2D models and their properties.
*   `live2d_model_name` (`str`): The name of the currently selected Live2D model.
*   `model_info` (`dict`): A dictionary containing detailed information about the loaded Live2D model, as retrieved from the `model_dict.json`.
*   `emo_map` (`dict`): A dictionary mapping lowercase emotion names (e.g., "joy", "sadness") to their corresponding expression indices (integers) used by the Live2D model. This is derived from the `emotionMap` within `model_info`.
*   `emo_str` (`str`): A formatted string containing examples of how emotion tags can be specified in text, including intensity values (e.g., `"[fear], [fear:0.3], [fear:0.7], [anger], [anger:0.3], [anger:0.7], ..."`. This string is useful for prompt engineering.

#### `__init__(self, live2d_model_name: str, model_dict_path: str = "model_dict.json")`
Initializes a new `Live2dModel` instance.

**Arguments:**
*   `live2d_model_name` (`str`): The name of the Live2D model to load. This name must match an entry in the `model_dict.json` file.
*   `model_dict_path` (`str`, optional): The path to the model dictionary JSON file. Defaults to `"model_dict.json"`.

#### `set_model(self, model_name: str) -> None`
Sets the current Live2D model by its name and loads its associated information, including the emotion map and the `emo_str`. This method is automatically called during object initialization.

**Arguments:**
*   `model_name` (`str`): The name of the Live2D model to be set.

#### `_load_file_content(self, file_path: str) -> str`
(Private Method) Loads the content of a file with robust encoding detection. It attempts to read the file using common encodings (`utf-8`, `utf-8-sig`, `gbk`, `gb2312`, `ascii`) and falls back to `chardet` for detection if initial attempts fail.

**Arguments:**
*   `file_path` (`str`): The path to the file to load.

**Returns:**
*   `str`: The decoded content of the file.

**Raises:**
*   `UnicodeError`: If the file cannot be decoded with any tried encoding.

#### `_lookup_model_info(self, model_name: str) -> dict`
(Private Method) Retrieves the detailed information for a specified Live2D model from the `model_dict.json` file.

**Arguments:**
*   `model_name` (`str`): The name of the Live2D model to look up.

**Returns:**
*   `dict`: A dictionary containing the information of the matched model.

**Raises:**
*   `FileNotFoundError`: If the `model_dict_path` is not found.
*   `json.JSONDecodeError`: If the `model_dict.json` file is not a valid JSON.
*   `UnicodeError`: If there's an error reading the `model_dict.json` file due to encoding issues.
*   `KeyError`: If the `model_name` is not found within the `model_dict.json`.

#### `extract_emotion(self, str_to_check: str) -> list`
Analyzes an input string to identify emotion keywords (e.g., `[emotion]`, `[emotion:intensity]`) and emojis, and returns a list of detected emotions with their corresponding expression indices and intensity values. Bracketed tags have higher precedence than emojis.

**Arguments:**
*   `str_to_check` (`str`): The string to parse for emotion keywords and emojis.

**Returns:**
*   `list`: A list of tuples, where each tuple is `(expression_index, intensity_value)`. An empty list is returned if no emotions are found. If no intensity is specified in a bracketed tag, it defaults to `1.0`. For emojis, the intensity always defaults to `1.0`.

#### `remove_emotion_keywords(self, target_str: str) -> str`
Removes all emotion keywords (e.g., `[emotion]`, `[emotion:intensity]`) from the input string and returns the cleaned string.

**Arguments:**
*   `target_str` (`str`): The string from which to remove emotion keywords.

**Returns:**
*   `str`: The string with emotion keywords removed.

#### `get_interpolated_expression(self, expression_index: int, intensity: float) -> dict`
Generates a dictionary payload for an interpolated Live2D expression. This method prepares the data (expression index and intensity) for transmission to the frontend, which will then handle the actual interpolation of the Live2D model's expression parameters.

**Arguments:**
*   `expression_index` (`int`): The index of the target expression.
*   `intensity` (`float`): The desired intensity of the expression, a float value between `0.0` and `1.0`. This value is clamped to ensure it stays within this range.

**Returns:**
*   `dict`: A dictionary in the format `{"expression_index": expression_index, "intensity": intensity}`.