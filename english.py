from collections import Counter, defaultdict
from itertools import chain

from util import apply_repeating_xor_key

# All bytes, from most common to least common in UTF-8-encoded English
# text. Data for this sequence is mostly taken from
# http://www.indiana.edu/~clcl/Papers/LFE.pdf. The paper does not
# mention certain characters, so I used my judgment as to where to put
# them, trying to come up with something that produces good results.
all_bytes_by_frequency = bytes(chain(
    b" ",    # Space, not mentioned in paper.

    # Characters in paper, from most common to least common.
    b"etaonisrhldcumfpgyw,.bv01k52TS\"9AM-CIN'438"
    b"B6RPEDHx7WLOFYGJzjUq:)($K;V*?Q/X&Z!%+><=#@",

    b"\n[\\]^_`{|}~\t\r",    # ASCII characters not mentioned in paper.

    # Continuation bytes in multi-byte characters (code points 0x80 -
    # 0x1fffff).
    range(0x80, 0xc0),

    # Leading byte of 2-byte characters (code points 0x80 - 0x7ff) that
    # occasionally appear in English text.
    range(0xc2, 0xe0),

    # Leading byte of 3-byte characters (code points 0x800 - 0xffff) that
    # rarely appear in English text.
    range(0xe0, 0xf0),

    # Leading byte of 4-byte characters (code points 0x10000 - 0x1fffff)
    # that rarely appear in English text.
    range(0xf0, 0xf5),

    # Control codes rarely used in practice.
    (x for x in range(0x00, 0x20) if bytes([x]) not in b"\n\t\r"),

    b"\x7f",    # Delete character rarely used in practice.

    range(0xc0, 0xc2),    # Overlong encoding, not valid UTF-8.

    range(0xf5, 0xf8),    # Overlong encoding, not valid UTF-8.

    range(0xf8, 0x100)    # Not valid UTF-8.
))

assert sorted(all_bytes_by_frequency) == list(range(256))


# Character frequencies were taken from raw letter averages at
# http://www.macfreek.nl/memory/Letter_Distribution, then rounded to 6
# decimal places for readability. Numbers for control characters (\x00
# through \x1f excluding tab (\x09), newline (\x0a), and carriage return
# (\x0d)) were added by me after observing better results. Text should
# be converted to lowercase before one attempts to analyze it using this
# dictionary.
lower_case_byte_frequencies = defaultdict(
    # The following number will be returned for any byte not explicitly
    # represented. 4e-6 was observed to produce the best ratio of score for
    # English text to score for incorrectly decrypted text.
    lambda: 4e-6,
    {ord(char): freq for char, freq in {
        "\x00": 1e-6, "\x01": 1e-6, "\x02": 1e-6, "\x03": 1e-6, "\x04": 1e-6,
        "\x05": 1e-6, "\x06": 1e-6, "\x07": 1e-6, "\x08": 1e-6, "\x0b": 1e-6,
        "\x0c": 1e-6, "\x0e": 1e-6, "\x0f": 1e-6, "\x10": 1e-6, "\x11": 1e-6,
        "\x12": 1e-6, "\x13": 1e-6, "\x14": 1e-6, "\x15": 1e-6, "\x16": 1e-6,
        "\x17": 1e-6, "\x18": 1e-6, "\x19": 1e-6, "\x1a": 1e-6, "\x1b": 1e-6,
        "\x1c": 1e-6, "\x1d": 1e-6, "\x1e": 1e-6, "\x1f": 1e-6,
        " ": 0.183169, "a": 0.065531, "b": 0.012708, "c": 0.022651, "d": 0.033523,
        "e": 0.102179, "f": 0.019718, "g": 0.016359, "h": 0.048622, "i": 0.057343,
        "j": 0.001144, "k": 0.005692, "l": 0.033562, "m": 0.020173, "n": 0.057031,
        "o": 0.062006, "p": 0.015031, "q": 0.000881, "r": 0.049720, "s": 0.053263,
        "t": 0.075100, "u": 0.022952, "v": 0.007880, "w": 0.016896, "x": 0.001498,
        "y": 0.014700, "z": 0.000598
    }.items()})


def english_like_score(text_bytes):
    # lower_case_byte_frequencies is defined outside of this function as a
    # performance optimization. In my tests, the time spent in this function
    # is less than half of what it would be if lower_case_byte_frequencies
    # were defined inside this function.
    text_length = len(text_bytes)
    chi_squared = 0
    for byte, byte_count in Counter(text_bytes.lower()).items():
        expected = text_length * lower_case_byte_frequencies[byte]
        difference = byte_count - expected
        chi_squared += difference * difference / expected
    return 1e6 / chi_squared / text_length


def xor_score_data(ciphertext, key):
    message = apply_repeating_xor_key(ciphertext, key)
    return {"key": key, "message": message, "score": english_like_score(message)}


def best_byte_xor_score_data(ciphertext):
    return max((xor_score_data(ciphertext, bytes([i])) for i in range(256)),
               key=lambda x: x["score"])


def crack_common_xor_key(ciphertexts):
    key = bytearray()
    for i in range(max(len(c) for c in ciphertexts)):
        transposed_block = bytes(c[i] for c in ciphertexts if i < len(c))
        key += best_byte_xor_score_data(transposed_block)["key"]
    return key
