from .pipeline import PhysicsConfig, generate_czml


def main():
    smoke_path, cloud_path = generate_czml(config=PhysicsConfig())
    print(f"Wrote {smoke_path}")
    print(f"Wrote {cloud_path}")


if __name__ == "__main__":
    main()
