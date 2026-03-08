good = []
with open("ospd.txt", 'r') as f:
    for l in f:
        l = l.strip()
        if len(l) == 5:
            good.append(l+"\n")

with open("clean-ospd.txt", 'w') as f:
    f.writelines(good)