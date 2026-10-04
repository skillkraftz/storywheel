# Dictionary, thesaurus and rhymes
Words (F5) and the Writer's lookup card (F7) work offline from an index built once on your machine.
## Installing
storywheel dictionary install downloads Open English WordNet (CC BY 4.0), the Moby Thesaurus (public domain) and the CMU Pronouncing Dictionary (for rhymes), about 40 MB, builds the index (~/.storywheel/dictionary.sqlite and rhymes.sqlite) and keeps the sources so a newer index can be rebuilt without the network. It is the only time storywheel uses the network. If the rhymes part fails, everything else still works and the install says so plainly; run it again to retry. storywheel dictionary status shows what is installed and the CMU license.
## From the command line
storywheel lookup WORD (or define, thesaurus) prints meanings, similar and opposite words; add --json for scripts.
## Rhymes
Perfect rhymes share the sound from the last stressed vowel and differ before it (cat, hat); near rhymes share the vowel with a similar ending, or the ending after a close vowel (cat, cap). Only words WordNet or Moby know are listed unless you choose "Names and rare words too". Words are ordered by how common they are when wordfreq is installed (pipx inject storywheel wordfreq), otherwise A to Z.
## Spelling
The same words feed the spellchecker's lists, so words the dictionary knows are not marked wrong.
