import json
from textwrap import fill

json_file = open('characters.json')
characters = json.load(json_file)
json_file.close()


def get_index(char_name, char_db):
    names = [sub["Name"] for sub in char_db["Characters"]]
    target_index = names.index(char_name)
    return target_index


def list_chars(char_db):
    names = [sub["Name"] for sub in char_db["Characters"]]
    return names


def char_basics(char_index, char_db):
    basics = []
    result = char_db["Characters"][char_index]
    basics.append("__**Name:**__ " + result["Name"] + "\n")
    basics.append("__**One Unique Thing:**__ " + result["One Unique Thing"] + "\n")
    basics.append("__**Backgrounds:**__")
    for k, v in result["Backgrounds"].items():
        basics.append("\t" + k + ": " + str(v))
    basics.append("\n__**Icons:**__")
    for k, v in result["Icons"].items():
        basics.append("\t" + k + ": " + v)
    basics.append("\n__**History:**__\n" + result["History"])
    return '\n'.join(basics)


def char_abilities(char_index, char_db):
    result = char_db["Characters"][char_index]["Abilities"]
    abilities = f"""
Abilities
{"=" * 40}
    Strength: {result['STR']['Stat']}\t\tModifier: {('+' if result['STR']['Modifier'] > 0 else "") + str(result['STR']['Modifier'])}
Constitution: {result['CON']['Stat']}\t\tModifier: {('+' if result['CON']['Modifier'] > 0 else "") + str(result['CON']['Modifier'])}
   Dexterity: {result['DEX']['Stat']}\t\tModifier: {('+' if result['DEX']['Modifier'] > 0 else "") + str(result['DEX']['Modifier'])}
Intelligence: {result['INT']['Stat']}\t\tModifier: {('+' if result['INT']['Modifier'] > 0 else "") + str(result['INT']['Modifier'])}
      Wisdom: {result['WIS']['Stat']}\t\tModifier: {('+' if result['WIS']['Modifier'] > 0 else "") + str(result['WIS']['Modifier'])}
    Charisma: {result['CHA']['Stat']}\t\tModifier: {('+' if result['CHA']['Modifier'] > 0 else "") + str(result['CHA']['Modifier'])}
"""
    return abilities

# print(list_chars(characters))
# print(char_basics(1, characters))
# print(char_abilities(get_index("Ragrik", characters), characters))
