# Embermail

## Directory structure

```text
root/
    embermail/          -> The base project directory
        settings.py
        drivers/        -> asgi.py and wsgi.py
        interface/      -> interface layer modules
        application/    -> application layer modules
        domain/         -> domain layer modules
        infrastructure/ -> infrastructure layer modules
    lib/                -> reusable modules
    external-apps/      -> apps not following the project's dev guidelines
    manage.py
    ...
```


## Development guidelines

### Tests

- Every module must include unit tests
- Tests should consider success and failure scenarios
- During the first development phase, code coverage should be at least of 80% per module, it should eventually be expanded to 100%

### Architecture

- Apps should be isolated
  - Each layer can only include direct calls to functions in lower layers (Interface > Application > Domain > Infrastructure)
  - The application layer is the main point of integration of domain APIs
  - Django apps should not include foreign keys to other django apps.
  - Interactions should be modelled as API/function calls.
  - Django signals can be used to decouple applications.
  - When using Django signals, handlers should be registered in the application layer, avoiding direct calls from one domain module to another.
  - When modules depend on each other directly use dependency inversion.

### Database

- Do not use DB generated ids for entities, use uuid4 instead
- Create model ids in the application, not the database
- For any given operation perform all DB writes atomically in a single transaction

### Style

- Throughout the code we use the word **build** to refer to methods that create objects in memory only and the word **create** to refer to methods that create objects in memory and write them to a storage medium.
- Do not add carriage returns to the end of files; Windows does this by default. Please configure your editor so they aren't saved into files.

#### Removing carriage returns from files

Windows carriage returns appear as the `^M` chars; you can remove them from
files with gnu sed (bsd sed won't work): `sed -i 's/\r//' <filename>`