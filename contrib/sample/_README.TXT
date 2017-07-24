To add an improved item to the sample wiki:

  * edit the item in your local wiki
  * in a console window, activate the Python environment
    * Unix: . activate
    * Windows: activate
  * Run the following command, replacing 3 instances of 'Home' with the target item name.
    * If the item is a subitem or has a leading namespace, then avoid creating
      subdirectories within contrib/sample by replacing the "/" in the names within the
      meta and data options with "-".

        moin item-get --name Home --meta contrib/sample/Home.meta --data contrib/sample/Home.data

  * Review the changes, do code review, commit, pull request, or push (whatever is appropriate)


To add or improve items with a non-ASCII names:
  * save your wiki data: ./m backup xxxxx
  * delete wiki: ./m del-wiki
  * restore unicode.moin: ./m restore contrib/sample/unicode.moin
  * make improvements (do not register new users or create unwanted items)
  * save the changes: ./m backup contrib/sample/unicode.moin
  * Review the changes, do code review, commit, pull request, or push (whatever is appropriate)


TODO: Find a cross-platform way to use "moin item-get/item-put" with a non-ASCII name.
All attempts, including the one below, result in a KeyError on Windows. As a workaround,
Items with non-ASCII names are in the file unicode.moin, a serialized dump file.

@echo on
for /f "tokens=2 delims=:." %%x in ('chcp') do set cp=%%x
chcp 65001
moin item-get --name StronaGlówna --meta contrib/sample/StronaGlówna.meta --data contrib/sample/StronaGlówna.data
chcp %cp%
