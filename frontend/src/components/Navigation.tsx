import React from 'react';
import { Link, useLocation } from 'react-router-dom';

export interface NavItem {
  label: string;
  path: string;
  icon?: React.ReactNode;
}

export interface NavigationProps {
  items: NavItem[];
  className?: string;
}

export const Navigation: React.FC<NavigationProps> = ({ items, className = '' }) => {
  const location = useLocation();
  
  return (
    <nav className={`${className}`}>
      <ul className="flex space-x-1">
        {items.map((item) => {
          const isActive = location.pathname === item.path;
          return (
            <li key={item.path}>
              <Link
                to={item.path}
                className={`
                  px-4 py-2 rounded-lg text-sm font-medium transition-colors
                  ${isActive
                    ? 'bg-primary-100 text-primary-700'
                    : 'text-secondary-600 hover:bg-secondary-100 hover:text-secondary-900'
                  }
                `}
              >
                {item.icon && <span className="mr-2">{item.icon}</span>}
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
};

export interface SidebarProps {
  items: NavItem[];
  className?: string;
}

export const Sidebar: React.FC<SidebarProps> = ({ items, className = '' }) => {
  const location = useLocation();
  
  return (
    <aside className={`w-64 bg-white border-r border-secondary-200 ${className}`}>
      <nav className="p-4">
        <ul className="space-y-1">
          {items.map((item) => {
            const isActive = location.pathname === item.path;
            return (
              <li key={item.path}>
                <Link
                  to={item.path}
                  className={`
                    flex items-center px-4 py-2 rounded-lg text-sm font-medium transition-colors
                    ${isActive
                      ? 'bg-primary-100 text-primary-700'
                      : 'text-secondary-600 hover:bg-secondary-100 hover:text-secondary-900'
                    }
                  `}
                >
                  {item.icon && <span className="mr-3">{item.icon}</span>}
                  {item.label}
                </Link>
              </li>
            );
          })}
        </ul>
      </nav>
    </aside>
  );
};

