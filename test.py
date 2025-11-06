import json
from demo import MyAgentModel

def main():
    model = MyAgentModel.load_from_checkpoint("checkpoints/best_model.pth")
    model.eval()

    total = 0
    correct = 0

    with open("valid/data.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            data = json.loads(line)
            query = data["query"]
            true_answer = data["answer"]

            pred = model.predict(query)

            total += 1
            if pred.strip() == true_answer.strip():
                correct += 1

    print(f"验证集准确率：{correct}/{total} = {correct / total:.2%}")

if __name__ == "__main__":
    main()
