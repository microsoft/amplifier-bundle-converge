# Community bulletin export

Accepted promise: a person can export an entire UTF-8 publication to a plain
text file through the documented command. Every character, paragraph and final
contact detail must be preserved. A preview is not a complete export.

Supported command:

```sh
python export.py publication.txt exported.txt
```

Worker return: the exporter and short-publication regression test are complete.
Both declared checks passed. Longer publications have not been manually reviewed.
The implementation owner remains responsible for any missing export behavior.

Declared checks:

```sh
python -m unittest discover -s . -p 'test_*.py'
python export.py --help
```

`publication.txt` is a supported example input. The return is awaiting independent
manager verification; it is not already accepted or integrated.
