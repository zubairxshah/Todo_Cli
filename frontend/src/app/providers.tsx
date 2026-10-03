'use client';

import { useEffect, useState } from 'react';

export function Providers({ children }: { children: React.ReactNode }) {
  const [isMounted, setIsMounted] = useState(false);

  useEffect(() => {
    setIsMounted(true);
  }, []);

  // Render children - auth will be handled at page level if needed
  if (!isMounted) {
    return <>{children}</>;
  }

  return <>{children}</>;
}