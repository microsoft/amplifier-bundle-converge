# sensorlog

A very small command-line tool that reads a sensor log and prints either the
full reading list or a one-line summary.

```
python -m sensorlog.cli report  samples/day.log
python -m sensorlog.cli summary samples/day.log
```

Run the tests:

```
python -m pytest -q
```

## Known rough edges

- A reading without a unit prints `?`. Nobody has decided whether that should
  be an error instead.
- `summary` averages only the commonest unit and says so; readings in other
  units are counted but not averaged.
