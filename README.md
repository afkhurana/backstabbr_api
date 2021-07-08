# **backstabbr_api**
This is an DIY API using urllib.request for Backstabbr.


## Usage
* Requests the status of all players and returns them as a set.
```python
get_submitted_countries()
```

* Requests the number of supply center for each country and returns them as a set. 
```python
get_supply_center_count()
```

## Example code:
```Python
from backstabbr_api import backstabbr_api as bs_api
import backstabbr_bot

def main():
    bsa = bs_api.BackstabbrAPI("[your session cookie, preferably as GM]", "[base link to your game]")
    submittedC = bsa.get_submitted_countries()
    supplyCC = bsa.get_supply_center_count()

    print(submittedC, "\n", supplyCC)

    for i in submittedC:
        print(i, submittedC[i])

    print()

    for i in supplyCC:
        print(i, supplyCC[i])



if __name__ == '__main__':
    main()
```

## TODO
* flesh out README and add more usage descriptions

## Author
[afkhurana](https://github.com/afkhurana)

## Contributors
[J0hnny007](https://github.com/J0hnny007)

## License
[MIT](https://choosealicense.com/licenses/mit/)