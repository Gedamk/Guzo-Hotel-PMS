import React from "react";

type TableProps = React.TableHTMLAttributes<HTMLTableElement> & {
  children: React.ReactNode;
};

export const Table: React.FC<TableProps> = ({ children, ...rest }) => {
  return <table {...rest}>{children}</table>;
};

type ThProps = React.ThHTMLAttributes<HTMLTableCellElement> & {
  children: React.ReactNode;
};

export const Th: React.FC<ThProps> = ({ children, ...rest }) => {
  return <th {...rest}>{children}</th>;
};

type TdProps = React.TdHTMLAttributes<HTMLTableCellElement> & {
  children: React.ReactNode;
};

export const Td: React.FC<TdProps> = ({ children, ...rest }) => {
  return <td {...rest}>{children}</td>;
};
