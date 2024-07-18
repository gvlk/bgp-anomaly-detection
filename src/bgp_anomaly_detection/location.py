import pickle
from pathlib import Path

from frozendict import frozendict
from pycountry import countries


def get_country_name(abbreviation: str) -> str:
    try:
        country = countries.get(alpha_2=abbreviation.upper())
        name = country.name
        if "," in name:
            parts = name.split(",")
            name = f"{parts[1].strip()} {parts[0]}"
        return name
    except (KeyError, AttributeError):
        return abbreviation


def make_location_dictionary(directory: str | Path, output_file: str | Path) -> None:
    location_dict = dict()

    for file_path in Path(directory).rglob("*.txt"):
        with open(file_path, "r") as file:
            for line in file:
                parts = line.strip().split('|')
                if len(parts) >= 4 and parts[2] == "asn":
                    as_id = parts[3]
                    location_abbr = parts[1]
                    location_full = get_country_name(location_abbr)
                    location_dict[as_id] = location_full

    with open(output_file, "wb") as output:
        pickle.dump(frozendict(location_dict), output)


def main():
    directory = Path("..", "data", "delegated")
    output_file = directory / "locale.pkl"
    make_location_dictionary(directory, output_file)


if __name__ == '__main__':
    main()
