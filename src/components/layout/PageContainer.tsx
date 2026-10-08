import React from 'react';

interface PageContainerProps {
  readonly children: React.ReactNode;
  readonly className?: string;
  readonly maxWidth?: 'full' | 'standard' | 'narrow';
}

export const PageContainer: React.FC<PageContainerProps> = ({
  children,
  className = '',
  maxWidth = 'standard',
}) => {
  const maxWidthClass =
    maxWidth === 'full'
      ? 'max-w-[1920px]'
      : maxWidth === 'narrow'
      ? 'max-w-5xl'
      : 'max-w-[1440px]';

  return (
    <main className={`w-full mx-auto px-4 sm:px-6 lg:px-8 py-6 ${maxWidthClass} ${className}`}>
      {children}
    </main>
  );
};
