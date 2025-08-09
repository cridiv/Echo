from apps import echo_brain

bot = echo_brain.EchoBrain()

while True:
    query = input("🧠 Ask Echo: ")
    if query.lower() in ["exit", "quit"]:
        break

    answer = bot.ask(query)
    print("🤖", answer)
