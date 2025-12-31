# Blueprint Architecture – Reference Viewer

This folder contains screenshots from Unreal Engine’s Reference Viewer for the main Blueprint classes of the project.
Each image visualizes the dependencies and relationships between core systems, helping illustrate the overall architecture.

These classes were chosen because they form the backbone of gameplay, combat, and game flow in Unreal Engine.

# Included Systems

- **Character**  
  The Character Blueprint represents all in-world controllable entities and AI.
  It is responsible for movement, combat state, spell casting, and animation logic.

- **Game Mode**  
  The GameMode defines the rules and flow of each game mode.
  It manages match state, win conditions, spawning logic, difficulty parameters, and multiplayer setup.

- **Player Controller**  
  The Player Controller handles player input, high-level decision making, and communication between the player and their Character.
  Input is intentionally processed at the controller level to keep the Character logic reusable for both players and AI.
  This separation allows clean multiplayer replication and consistent behavior across game modes.

- **Projectile**  
  Spells are implemented as Projectile-based Blueprints.
  Each spell inherits from a shared base class and customizes behavior such as movement, collision, damage, and special effects.

These diagrams are intended to provide a high-level understanding of the architecture of the game.

