class AS:
    def __init__(self, as_id: str) -> None:
        try:
            int(as_id)
        except ValueError:
            raise ValueError(f"Invalid AS identifier: '{as_id}' is not a valid integer.")
        else:
            self.id = str(as_id)

        self.times_seen: int = int()
        self.n_mid_path: int = int()
        self.n_end_path: int = int()
        self.path_sizes: list[int] = list()
        self.announced_prefixes: set[str] = set()
        self.neighbours: set[AS] = set()

    def __repr__(self):
        return f"AS {self.id}"
