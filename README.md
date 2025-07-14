# Word-Hunter
A XY gantry system to play the GamePigeon game Word Hunt. Project for Hack Club Undercity!

<img width="844" height="634" alt="image" src="https://github.com/user-attachments/assets/873782df-94c3-4f82-9829-089fa519c28a" />

A Camera module takes a picture of the board. It then uploads the image to OpenAI's 4o model to read and process the letters on the screen. The Python script then uses a dictionary file to generate the best words and their swipe paths, which is sent to the XY gantry system with two stepper motors holding an Apple Pencil to play the game.
