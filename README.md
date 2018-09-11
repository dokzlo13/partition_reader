# Partition Reader [![N|Solid](https://www.python.org/static/community_logos/python-powered-w-140x56.png)](https://www.python.org/) 
Скрипт для чтения основных форматов таблиц разделов (MBR, GPT, BSD DiskLabel)

# Установка
Клонируйте репозиторий
```sh
$ git clone https://github.com/dokzlo13/partition_reader.git
```
Запуск
```sh
$ cd partition_reader
$ python3 ./partition.py image1 image2 ...
```
или
```sh
$ python2.7 ./partition.py image1 image2 ...
```
Пример работы:
![Пример работы](https://s33.postimg.cc/3xs32ln1b/screen-2018-09-11-14-09-12.png)

- При указании ключа -l (--log) вывод будет записан в файл partition.log в рабочем каталоге

Данный проект был реализован с применением исходных кодов проекта:
https://github.com/jrd/pyreadpartitions