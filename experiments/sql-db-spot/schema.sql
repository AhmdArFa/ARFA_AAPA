CREATE TABLE dealerships (
  dealership_id INTEGER PRIMARY KEY,
  name TEXT NOT NULL,
  state TEXT NOT NULL,
  year_established INTEGER NOT NULL,
  num_employees INTEGER NOT NULL
);
CREATE TABLE cars (
  serial_num TEXT PRIMARY KEY,
  make TEXT NOT NULL,
  model TEXT NOT NULL,
  mpg REAL NOT NULL,
  total_miles INTEGER NOT NULL
);
CREATE TABLE sales (
  sale_id INTEGER PRIMARY KEY,
  serial_num TEXT NOT NULL REFERENCES cars(serial_num),
  dealership_id INTEGER NOT NULL REFERENCES dealerships(dealership_id),
  owner_ref INTEGER NOT NULL,
  sale_price REAL NOT NULL,
  sale_date TEXT NOT NULL,
  payment_method TEXT NOT NULL,
  financing_type TEXT
);
CREATE TABLE service_records (
  service_id INTEGER PRIMARY KEY,
  serial_num TEXT NOT NULL REFERENCES cars(serial_num),
  service_center TEXT NOT NULL,
  service_type TEXT NOT NULL,
  service_cost REAL NOT NULL,
  service_date TEXT NOT NULL,
  warranty_covered INTEGER NOT NULL,
  service_manager_ref INTEGER NOT NULL
);
