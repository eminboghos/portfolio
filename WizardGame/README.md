# Wizard Combat Game
My first large-scale Unreal Engine 5 project.  A wizard combat game built around casting spells, adaptive AI, and multiple game modes.
This game is built around reactive combat and system interactions rather than scripted sequences. 
Each mechanic is designed to interact with others, creating emergent gameplay. 
This game has :
  - 4 game modes, including one multiplayer mode
  - 6 spells combined with a shield system
  - Spell–spell and spell–environment interactions
  - Adaptive AI with severall difficulty levels that reacts to player behavior

### Full Gameplay Videos
This project is actively under development.  
Gameplay footage represents a work-in-progress build focused on demonstrating systems and mechanics rather than final polish.
- Arena Mode: [https://www.youtube.com/watch?v=XXXX](https://www.youtube.com/watch?v=RBqKmq2vxv8)
- 1v1 Mode: [https://www.youtube.com/watch?v=YYYY](https://www.youtube.com/watch?v=aQS5SNE5Reo)
- Teamfight Mode: [https://www.youtube.com/watch?v=ZZZZ](https://www.youtube.com/watch?v=ZFREk5n1Z_Q)

## Technical Implementation

The project was developed entirely in Unreal Engine 5, with the majority of gameplay systems implemented using Blueprints. From the start, the focus was on building reusable and scalable systems rather than isolated, one-off mechanics, which became essential as the project grew in size and complexity.

Gameplay logic is structured around an object-oriented Blueprint architecture, with shared base classes defining common behavior and child classes handling specific variations. This approach made it possible to extend features such as spells, characters, and interactions without rewriting core logic.

Combat systems are designed in an event-driven way, allowing spells, shields, and environmental interactions to communicate through interfaces and events. This keeps systems easier to maintain or expand.


## AI System

The AI system was the most complex and challenging part of the project. AI logic is implemented using Unreal Engine’s Behavior Trees and Blackboards. This structure helped manage complexity, but required careful design to avoid brittle or unpredictable behavior as new mechanics were added.

The same core AI logic is reused across all difficulty levels. Instead of scaling health or damage, difficulty is handled by adjusting behavioral parameters such as reaction timing, positioning, spell selection, and aggression thresholds. The AI also adapts over time to the player’s playstyle, responding differently to the player’s reactivity.

## Multiplayer

Multiplayer functionality was implemented using a client–server architecture, where one player acts as the host (server) and all other players connect as clients. Gameplay logic is primarily server-authoritative, using Unreal Engine’s built-in replication system to synchronize player states, spells, and world interactions. 

To avoid giving the host an inherent latency advantage, many gameplay events are first evaluated on the client and then validated and propagated by the server. This approach prioritizes fairness in moment-to-moment combat. Through testing, the system remained fair and playable with no noticeable advantage for either the server or the clients up to around 200 ms of network delay. Beyond this threshold, latency becomes apparent and begins to affect timing-critical interactions, which is expected given the fast paced nature of the game.

## What I Learned

This project was a major step in improving how I approach system design, scalability, complexity management and optimization in game development. Working on a full-scale Unreal Engine 5 project with multiple interconnected systems taught me to think about both the architecture and the gameplay impact of every decision.
