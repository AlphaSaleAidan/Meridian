-- Add phone column to schedule_staff so publish can send shift SMS.
alter table schedule_staff
  add column if not exists phone text;
