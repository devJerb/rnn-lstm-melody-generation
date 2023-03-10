import json
import numpy as np
import music21 as m21
import tensorflow.keras as keras
from preprocess import SEQUENCE_LENGTH, MAPPING_PATH

TEMPERATURE = 0.5


class MelodyGenerator:
    def __init__(self, model_path="model.h5"):
        self.model_path = model_path
        self.model = keras.models.load_model(model_path)

        with open(MAPPING_PATH, "r") as fp:
            self._mappings = json.load(fp)

        self._start_symbols = ["/"] * SEQUENCE_LENGTH

    def generate_melody(self, seed, num_steps, max_sequence_length, temperature):
        # create seed with start symbols
        seed = seed.split()
        melody = seed
        seed = self._start_symbols + seed

        # map seed to int
        seed = [self._mappings[symbol] for symbol in seed]

        for _ in range(num_steps):
            # limit the seed to max_sequence_length
            seed = seed[-max_sequence_length:]

            # one-hot encode the seed
            onehot_seed = keras.utils.to_categorical(seed, num_classes=len(self._mappings))

            # (1, max_sequence_length, num of symbols in the vocabulary)
            onehot_seed = onehot_seed[np.newaxis, ...]

            # max a prediction
            probabilities = self.model.predict(onehot_seed)[0]

            # [0.1, 0.2, 0.1, 0.6] -> 1
            output_int = self._sample_with_temperature(probabilities, temperature)

            # update seed
            seed.append(output_int)

            # map int to our encoding
            output_symbol = [key for key, value in self._mappings.items() if value == output_int][0]

            # check the end of a melody
            if output_symbol == "/":
                break

            # update the melody
            melody.append(output_symbol)

        return melody

    def _sample_with_temperature(self, probabilities, temperature):
        # temperature -> infinity
        # temperature -> 0
        # temperature = 1
        predictions = np.log(probabilities) / temperature
        probabilities = np.exp(predictions) / np.sum(np.exp(predictions))

        choices = range(len(probabilities))  # [0, 1, 2, 3]
        index = np.random.choice(choices, p=probabilities)

        return index

    def save_melody(self, melody, step_duration=0.25, format="midi", file_name="melody.midi"):
        # create a m21 stream
        stream = m21.stream.Stream()

        # parse all the symbols in the melody and create note/rest objects
        start_symbol = None
        step_counter = 1

        for i, symbol in enumerate(melody):
            # handle case in which we have a note/rest
            if symbol != "_" or i + 1 == len(melody):
                # ensure we're dealing with note/rest beyond the first note/rest
                if start_symbol is not None:
                    quarter_length_duration = step_duration * step_counter  # 0.25 * 4 = 1
                    # handle rest
                    if start_symbol == "r":
                        m21_event = m21.note.Rest(quarterLength=quarter_length_duration)
                    # handle note
                    else:
                        m21_event = m21.note.Note(int(start_symbol), quarterLength=quarter_length_duration)
                    stream.append(m21_event)

                    # reset the step counter
                    step_counter = 1

                start_symbol = symbol
            # handle case in which we have a prolongation sign "_"
            else:
                step_counter += 1
        # write the m21 stream to a midi file
        stream.write(format, file_name)


melody_generator = MelodyGenerator()
seed1 = "64 _ 69 _ _ _ 71 _ 72 _ _ 71 69 _ 76 _ _ _ _ _"
seed2 = "71 _ _ _ 74 _ 72 _ _ 71 69 _ 68 _ _ _ 69 _ 71"

# higher temperature means more unpredictable
melody = melody_generator.generate_melody(seed2, 500, SEQUENCE_LENGTH, TEMPERATURE)
print(melody)
melody_generator.save_melody(melody)
