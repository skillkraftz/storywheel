"""A tiny dictionary index built from a hand-made WordNet-style file and Moby-style lines (the real ones are downloaded by
`storywheel dictionary install`; tests never touch the network)."""
from storywheel import dictionary_build

XML = """<?xml version="1.0" encoding="UTF-8"?>
<LexicalResource xmlns:dc="https://globalwordnet.github.io/schemas/dc/">
  <Lexicon id="oewn" label="Open English Wordnet" language="en" email="x@y" license="https://creativecommons.org/licenses/by/4.0" version="2025" url="x">
    <LexicalEntry id="oewn-dog-n"><Lemma writtenForm="dog" partOfSpeech="n"/>
      <Sense id="oewn-dog__1.05.00.." synset="oewn-1-n"><SenseRelation relType="derivation" target="oewn-doggy__3.00.00.."/></Sense><Sense id="oewn-dog__1.18.01.." synset="oewn-2-n"/></LexicalEntry>
    <LexicalEntry id="oewn-doggy-a"><Lemma writtenForm="doggy" partOfSpeech="a"/><Sense id="oewn-doggy__3.00.00.." synset="oewn-12-a"/></LexicalEntry>
    <LexicalEntry id="oewn-puppy-n"><Lemma writtenForm="puppy" partOfSpeech="n"/><Sense id="oewn-puppy__1.05.00.." synset="oewn-13-n"/></LexicalEntry>
    <LexicalEntry id="oewn-pup-n"><Lemma writtenForm="pup" partOfSpeech="n"/><Sense id="oewn-pup__1.05.00.." synset="oewn-13-n"/></LexicalEntry>
    <LexicalEntry id="oewn-tail-n"><Lemma writtenForm="tail" partOfSpeech="n"/><Sense id="oewn-tail__1.05.00.." synset="oewn-14-n"/></LexicalEntry>
    <LexicalEntry id="oewn-kennel-n"><Lemma writtenForm="kennel" partOfSpeech="n"/><Sense id="oewn-kennel__1.06.00.." synset="oewn-15-n"/></LexicalEntry>
    <LexicalEntry id="oewn-veterinary-n"><Lemma writtenForm="veterinary medicine" partOfSpeech="n"/><Sense id="oewn-vet__1.09.00.." synset="oewn-16-n"/></LexicalEntry>
    <LexicalEntry id="oewn-vaccinate-v"><Lemma writtenForm="vaccinate" partOfSpeech="v"/><Sense id="oewn-vaccinate__2.00.00.." synset="oewn-17-v"/></LexicalEntry>
    <LexicalEntry id="oewn-domestic_dog-n"><Lemma writtenForm="domestic dog" partOfSpeech="n"/><Sense id="oewn-domestic_dog__1.05.00.." synset="oewn-1-n"/></LexicalEntry>
    <LexicalEntry id="oewn-canine-n"><Lemma writtenForm="canine" partOfSpeech="n"/><Sense id="oewn-canine__1.05.00.." synset="oewn-3-n"/></LexicalEntry>
    <LexicalEntry id="oewn-wretch-n"><Lemma writtenForm="wretch" partOfSpeech="n"/><Sense id="oewn-wretch__1.18.00.." synset="oewn-2-n"/></LexicalEntry>
    <LexicalEntry id="oewn-goose-n"><Lemma writtenForm="goose" partOfSpeech="n"/><Form writtenForm="geese"/><Sense id="oewn-goose__1.05.00.." synset="oewn-4-n"/></LexicalEntry>
    <LexicalEntry id="oewn-wolf-n"><Lemma writtenForm="wolf" partOfSpeech="n"/><Form writtenForm="wolves"/><Sense id="oewn-wolf__1.05.00.." synset="oewn-5-n"/></LexicalEntry>
    <LexicalEntry id="oewn-run-v"><Lemma writtenForm="run" partOfSpeech="v"/><Form writtenForm="ran"/><Sense id="oewn-run__2.38.00.." synset="oewn-6-v"/></LexicalEntry>
    <LexicalEntry id="oewn-sprint-v"><Lemma writtenForm="sprint" partOfSpeech="v"/><Sense id="oewn-sprint__2.38.00.." synset="oewn-6-v"/></LexicalEntry>
    <LexicalEntry id="oewn-dash-v"><Lemma writtenForm="dash" partOfSpeech="v"/><Sense id="oewn-dash__2.38.00.." synset="oewn-6-v"/></LexicalEntry>
    <LexicalEntry id="oewn-happy-a"><Lemma writtenForm="happy" partOfSpeech="a"/>
      <Sense id="oewn-happy__3.00.00.." synset="oewn-7-a"><SenseRelation relType="antonym" target="oewn-unhappy__3.00.00.."/></Sense></LexicalEntry>
    <LexicalEntry id="oewn-glad-a"><Lemma writtenForm="glad" partOfSpeech="a"/>
      <Sense id="oewn-glad__3.00.00.." synset="oewn-7-a"><SenseRelation relType="antonym" target="oewn-sad__3.00.00.."/></Sense></LexicalEntry>
    <LexicalEntry id="oewn-sad-a"><Lemma writtenForm="sad" partOfSpeech="a"/>
      <Sense id="oewn-sad__3.00.00.." synset="oewn-18-a"><SenseRelation relType="antonym" target="oewn-glad__3.00.00.."/></Sense></LexicalEntry>
    <LexicalEntry id="oewn-unhappy-a"><Lemma writtenForm="unhappy" partOfSpeech="a"/>
      <Sense id="oewn-unhappy__3.00.00.." synset="oewn-8-a"><SenseRelation relType="antonym" target="oewn-happy__3.00.00.."/></Sense></LexicalEntry>
    <LexicalEntry id="oewn-cheerful-s"><Lemma writtenForm="cheerful" partOfSpeech="s"/><Sense id="oewn-cheerful__3.00.01.." synset="oewn-9-s"/></LexicalEntry>
    <LexicalEntry id="oewn-leaf-n"><Lemma writtenForm="leaf" partOfSpeech="n"/><Form writtenForm="leaves"/><Sense id="oewn-leaf__1.20.00.." synset="oewn-10-n"/></LexicalEntry>
    <LexicalEntry id="oewn-leave-v"><Lemma writtenForm="leave" partOfSpeech="v"/><Sense id="oewn-leave__2.38.01.." synset="oewn-11-v"/></LexicalEntry>
    <Synset lexfile="noun.animal" id="oewn-1-n" members="oewn-dog-n oewn-domestic_dog-n" partOfSpeech="n"><Definition>a domesticated canine</Definition>
      <Example>the dog barked</Example><SynsetRelation relType="hypernym" target="oewn-3-n"/><SynsetRelation relType="hyponym" target="oewn-13-n"/>
      <SynsetRelation relType="mero_part" target="oewn-14-n"/><SynsetRelation relType="domain_topic" target="oewn-16-n"/></Synset>
    <Synset lexfile="adj.all" id="oewn-12-a" members="oewn-doggy-a" partOfSpeech="a"><Definition>like a dog</Definition></Synset>
    <Synset lexfile="noun.animal" id="oewn-13-n" members="oewn-puppy-n oewn-pup-n" partOfSpeech="n"><Definition>a young dog</Definition><SynsetRelation relType="hypernym" target="oewn-1-n"/></Synset>
    <Synset lexfile="noun.body" id="oewn-14-n" members="oewn-tail-n" partOfSpeech="n"><Definition>the rear appendage</Definition><SynsetRelation relType="holo_part" target="oewn-1-n"/></Synset>
    <Synset lexfile="noun.artifact" id="oewn-15-n" members="oewn-kennel-n" partOfSpeech="n"><Definition>a shelter for dogs</Definition><SynsetRelation relType="domain_topic" target="oewn-16-n"/></Synset>
    <Synset lexfile="noun.cognition" id="oewn-16-n" members="oewn-veterinary-n" partOfSpeech="n"><Definition>the branch of medicine for animals</Definition>
      <SynsetRelation relType="has_domain_topic" target="oewn-1-n"/><SynsetRelation relType="has_domain_topic" target="oewn-15-n"/><SynsetRelation relType="has_domain_topic" target="oewn-17-v"/></Synset>
    <Synset lexfile="verb.change" id="oewn-17-v" members="oewn-vaccinate-v" partOfSpeech="v"><Definition>inoculate against disease</Definition><SynsetRelation relType="domain_topic" target="oewn-16-n"/></Synset>
    <Synset lexfile="noun.person" id="oewn-2-n" members="oewn-dog-n oewn-wretch-n" partOfSpeech="n"><Definition>a despicable person</Definition></Synset>
    <Synset lexfile="noun.animal" id="oewn-3-n" members="oewn-canine-n" partOfSpeech="n"><Definition>any of various fissiped mammals</Definition></Synset>
    <Synset lexfile="noun.animal" id="oewn-4-n" members="oewn-goose-n" partOfSpeech="n"><Definition>web-footed long-necked birds</Definition></Synset>
    <Synset lexfile="noun.animal" id="oewn-5-n" members="oewn-wolf-n" partOfSpeech="n"><Definition>a wild canine</Definition></Synset>
    <Synset lexfile="verb.motion" id="oewn-6-v" members="oewn-run-v oewn-sprint-v oewn-dash-v" partOfSpeech="v"><Definition>move fast by using legs</Definition><Example>She ran home</Example></Synset>
    <Synset lexfile="adj.all" id="oewn-7-a" members="oewn-happy-a oewn-glad-a" partOfSpeech="a"><Definition>enjoying or showing joy</Definition></Synset>
    <Synset lexfile="adj.all" id="oewn-18-a" members="oewn-sad-a" partOfSpeech="a"><Definition>feeling sorrow</Definition></Synset>
    <Synset lexfile="adj.all" id="oewn-8-a" members="oewn-unhappy-a" partOfSpeech="a"><Definition>experiencing sorrow</Definition></Synset>
    <Synset lexfile="adj.all" id="oewn-9-s" members="oewn-cheerful-s" partOfSpeech="s"><Definition>full of good spirits</Definition><SynsetRelation relType="similar" target="oewn-7-a"/></Synset>
    <Synset lexfile="noun.plant" id="oewn-10-n" members="oewn-leaf-n" partOfSpeech="n"><Definition>the main organ of photosynthesis</Definition></Synset>
    <Synset lexfile="verb.motion" id="oewn-11-v" members="oewn-leave-v" partOfSpeech="v"><Definition>go away from</Definition></Synset>
  </Lexicon>
</LexicalResource>
"""

MOBY = ("happy,glad,joyful,blithe,content,merry,cheerful,elated\r\n"
        "run,dash,sprint,jog,scamper,race,bolt,gallop\r\n"
        "dog,hound,mutt,pooch,cur\r\n"
        "leave,depart,exit,quit,go away\r\n"
        "unhappy,sad,miserable,glum\r\n")


def build_fixture(directory):
    directory = __import__("pathlib").Path(directory)
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "oewn.xml").write_text(XML, encoding="utf-8")
    (directory / "moby.txt").write_text(MOBY, encoding="latin-1")
    out = directory / "dictionary.sqlite"
    counts = dictionary_build.build(directory / "oewn.xml", directory / "moby.txt", out)
    return out, counts


# Zipf frequencies for the fixture's words (the real ones come from the wordfreq package)
ZIPF = {"puppy": 3.4, "tail": 4.6, "kennel": 2.6, "wretch": 2.0, "canine": 2.8, "sprint": 3.3, "dash": 3.9, "happy": 5.4, "unhappy": 3.5,
        "cheerful": 3.1, "vaccinate": 1.8, "doggy": 1.2, "veterinary": 2.4, "goose": 3.7, "wolf": 3.9, "leaf": 4.1, "leave": 5.5, "glad": 4.4,
        "sad": 4.9, "dog": 5.2, "hound": 3.0, "mutt": 2.1}
