import json
import chardet
from loguru import logger

# This class will only prepare the payload for the live2d model
# the process of sending the payload should be done by the caller
# This class is **Not responsible** for sending the payload to the server


class Live2dModel:
    """
    A class to represent a Live2D model. This class only prepares and stores the information of the Live2D model. It does not send anything to the frontend or server or anything.

    Attributes:
        model_dict_path (str): The path to the model dictionary file.
        live2d_model_name (str): The name of the Live2D model.
        model_info (dict): The information of the Live2D model.
        emo_map (dict): The emotion map of the Live2D model.
        emo_str (str): The string representation of the emotion map of the Live2D model.
    """

    model_dict_path: str
    live2d_model_name: str
    model_info: dict
    emo_map: dict
    emo_str: str

    def __init__(
        self, live2d_model_name: str, model_dict_path: str = "model_dict.json"
    ):
        self.model_dict_path: str = model_dict_path
        self.live2d_model_name: str = live2d_model_name
        self.set_model(live2d_model_name)

    def set_model(self, model_name: str) -> None:
        """
        Set the model with its name and load the model information. This method will initialize the `self.model_info`, `self.emo_map`, and `self.emo_str` attributes.
        This method is called in the constructor.

        Parameters:
            model_name (str): The name of the live2d model.

            Returns:
            None
        """

        self.model_info: dict = self._lookup_model_info(model_name)
        self.emo_map: dict = {
            k.lower(): v for k, v in self.model_info["emotionMap"].items()
        }

        # Generate emotion string with both formats: [emotion] and [emotion:intensity]
        emotion_examples = []
        for key in self.emo_map.keys():
            # Add basic format
            emotion_examples.append(f"[{key}]")
            # Add intensity format examples
            emotion_examples.append(f"[{key}:0.3]")
            emotion_examples.append(f"[{key}:0.7]")

        self.emo_str: str = " ".join([f"{example}," for example in emotion_examples])
        # emo_str is a string of the keys in the emoMap dictionary with examples of intensity values.
        # example: `"[fear], [fear:0.3], [fear:0.7], [anger], [anger:0.3], [anger:0.7], ..."`

    def _load_file_content(self, file_path: str) -> str:
        """Load the content of a file with robust encoding handling."""
        # Try common encodings first
        encodings = ["utf-8", "utf-8-sig", "gbk", "gb2312", "ascii"]

        for encoding in encodings:
            try:
                with open(file_path, "r", encoding=encoding) as file:
                    return file.read()
            except UnicodeDecodeError:
                continue

        # If all common encodings fail, try to detect encoding
        try:
            with open(file_path, "rb") as file:
                raw_data = file.read()
            detected = chardet.detect(raw_data)
            detected_encoding = detected["encoding"]

            if detected_encoding:
                try:
                    return raw_data.decode(detected_encoding)
                except UnicodeDecodeError:
                    pass
        except Exception as e:
            logger.error(f"Error detecting encoding for {file_path}: {e}")

        raise UnicodeError(f"Failed to decode {file_path} with any encoding")

    def _lookup_model_info(self, model_name: str) -> dict:
        """
        Find the model information from the model dictionary and return the information about the matched model.

        Parameters:
            model_name (str): The name of the live2d model.

        Returns:
            dict: The dictionary with the information of the matched model.

        Raises:
            FileNotFoundError if the model dictionary file is not found.

            json.JSONDecodeError if the model dictionary file is not a valid JSON file.

            KeyError if the model name is not found in the model dictionary.

        """

        self.live2d_model_name = model_name

        try:
            file_content = self._load_file_content(self.model_dict_path)
            model_dict = json.loads(file_content)
        except FileNotFoundError as file_e:
            logger.critical(
                f"Model dictionary file not found at {self.model_dict_path}."
            )
            raise file_e
        except json.JSONDecodeError as json_e:
            logger.critical(
                f"Error decoding JSON from model dictionary file at {self.model_dict_path}."
            )
            raise json_e
        except UnicodeError as uni_e:
            logger.critical(
                f"Error reading model dictionary file at {self.model_dict_path}."
            )
            raise uni_e
        except Exception as e:
            logger.critical(
                f"Error occurred while reading model dictionary file at {self.model_dict_path}."
            )
            raise e

        # Find the model in the model_dict
        matched_model = next(
            (model for model in model_dict if model["name"] == model_name), None
        )

        if matched_model is None:
            logger.critical(f"Unable to find {model_name} in {self.model_dict_path}.")
            raise KeyError(
                f"{model_name} not found in model dictionary {self.model_dict_path}."
            )

        # The feature: "translate model url to full url if it starts with '/' " is no longer implemented here

        logger.info("Model Information Loaded.")

        return matched_model

    def extract_emotion(self, str_to_check: str) -> list:
        """
        Check the input string for any emotion keywords and return a list of tuples containing
        the expression index and intensity value of the emotions found in the string.

        Parameters:
            str_to_check (str): The string to check for emotions.

        Returns:
            list: A list of tuples (expression_index, intensity_value) of the emotions found in the string.
                 An empty list is returned if no emotions are found.
                 For backward compatibility, if no intensity is specified, it defaults to 1.0.
        """
        import re

        # Regular expression to match both formats:
        # [emotion] and [emotion:intensity]
        emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'

        expression_list = []
        str_to_check = str_to_check.lower()

        # Find all emotion tags in the text
        matches = re.finditer(emotion_pattern, str_to_check)

        for match in matches:
            emotion = match.group(1)
            intensity_str = match.group(2)

            # Check if the emotion exists in our emotion map
            if emotion in self.emo_map:
                # Get the expression index
                expression_index = self.emo_map[emotion]

                # Parse intensity value, default to 1.0 if not specified
                intensity = 1.0
                if intensity_str:
                    try:
                        intensity = float(intensity_str)
                        # Clamp intensity to valid range [0.0, 1.0]
                        intensity = max(0.0, min(1.0, intensity))
                    except ValueError:
                        # If conversion fails, use default intensity
                        intensity = 1.0

                expression_list.append((expression_index, intensity))

        return expression_list

    def remove_emotion_keywords(self, target_str: str) -> str:
        """
        Remove the emotion keywords from the input string and return the cleaned string.
        Handles both [emotion] and [emotion:intensity] formats.

        Parameters:
            str_to_check (str): The string to check for emotions.

        Returns:
            str: The cleaned string with the emotion keywords removed.
        """
        import re

        # Regular expression to match both formats:
        # [emotion] and [emotion:intensity]
        emotion_pattern = r'\[([\w]+)(?::([0-9]*\.?[0-9]+))?\]'

        # Replace all emotion tags with empty string
        cleaned_str = re.sub(emotion_pattern, '', target_str)

        return cleaned_str

    def get_interpolated_expression(self, expression_index: int, intensity: float) -> dict:
        """
        Generate interpolated expression parameters based on intensity.

        This method interpolates between the neutral expression (index 0) and the target emotion
        based on the provided intensity value.

        Parameters:
            expression_index (int): The index of the target expression.
            intensity (float): The intensity value between 0.0 and 1.0.

        Returns:
            dict: A dictionary containing the interpolated expression parameters.
                 Format: {"expression_index": expression_index, "intensity": intensity}

        Note:
            The actual interpolation of expression parameters is handled by the frontend.
            This method simply packages the expression index and intensity for transmission.
        """
        # Ensure intensity is within valid range
        intensity = max(0.0, min(1.0, intensity))

        # Create a dictionary with the expression index and intensity
        interpolated_expression = {
            "expression_index": expression_index,
            "intensity": intensity
        }

        return interpolated_expression
