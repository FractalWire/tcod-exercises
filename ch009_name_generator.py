import tcod


def main() -> None:
    tcod.namegen_parse('data/names/name_tcod_structures.dat')
    print(*[tcod.namegen_generate("Male") for _ in range(10)], sep='\n')
    print(*[tcod.namegen_generate("Female") for _ in range(10)], sep='\n')


if __name__ == "__main__":
    main()
